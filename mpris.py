"""Minimal MPRIS v2 D-Bus service for EchoYT.

Implemented with jeepney (pure Python, no GLib), so it can run inside the Qt
process without the crashes caused by loading the native ``mpv-mpris`` plugin
into a process that also uses libmpv.

The service owns ``org.mpris.MediaPlayer2.echoyt`` and exports the standard
``/org/mpris/MediaPlayer2`` object, so desktop "now playing" widgets, media
keys and ``playerctl`` can see and control playback.
"""

import logging
import threading

from jeepney import (
    DBusAddress,
    HeaderFields,
    MessageType,
    new_error,
    new_method_return,
    new_signal,
)
from jeepney.bus_messages import DBus
from jeepney.io.blocking import open_dbus_connection

log = logging.getLogger(__name__)

BUS_NAME = "org.mpris.MediaPlayer2.echoyt"
OBJECT_PATH = "/org/mpris/MediaPlayer2"
IFACE_ROOT = "org.mpris.MediaPlayer2"
IFACE_PLAYER = "org.mpris.MediaPlayer2.Player"
IFACE_PROPS = "org.freedesktop.DBus.Properties"
IFACE_INTROSPECT = "org.freedesktop.DBus.Introspectable"

TRACK_PATH_BASE = "/org/mpris/MediaPlayer2/Track/"

INTROSPECTION_XML = f"""<!DOCTYPE node PUBLIC '-//freedesktop//DTD D-BUS Object Introspection 1.0//EN'
'http://www.freedesktop.org/standards/dbus/1.0/introspect.dtd'>
<node>
  <interface name='{IFACE_ROOT}'>
    <method name='Raise'/>
    <method name='Quit'/>
    <property name='CanQuit' type='b' access='read'/>
    <property name='CanRaise' type='b' access='read'/>
    <property name='HasTrackList' type='b' access='read'/>
    <property name='Identity' type='s' access='read'/>
    <property name='DesktopEntry' type='s' access='read'/>
    <property name='SupportedUriSchemes' type='as' access='read'/>
    <property name='SupportedMimeTypes' type='as' access='read'/>
  </interface>
  <interface name='{IFACE_PLAYER}'>
    <method name='Next'/>
    <method name='Previous'/>
    <method name='Pause'/>
    <method name='PlayPause'/>
    <method name='Stop'/>
    <method name='Play'/>
    <method name='Seek'><arg direction='in' name='Offset' type='x'/></method>
    <method name='SetPosition'>
      <arg direction='in' name='TrackId' type='o'/>
      <arg direction='in' name='Position' type='x'/>
    </method>
    <method name='OpenUri'><arg direction='in' name='Uri' type='s'/></method>
    <signal name='Seeked'><arg name='Position' type='x'/></signal>
    <property name='PlaybackStatus' type='s' access='read'/>
    <property name='LoopStatus' type='s' access='readwrite'/>
    <property name='Rate' type='d' access='readwrite'/>
    <property name='Shuffle' type='b' access='readwrite'/>
    <property name='Metadata' type='a{{sv}}' access='read'/>
    <property name='Volume' type='d' access='readwrite'/>
    <property name='Position' type='x' access='read'/>
    <property name='MinimumRate' type='d' access='read'/>
    <property name='MaximumRate' type='d' access='read'/>
    <property name='CanGoNext' type='b' access='read'/>
    <property name='CanGoPrevious' type='b' access='read'/>
    <property name='CanPlay' type='b' access='read'/>
    <property name='CanPause' type='b' access='read'/>
    <property name='CanSeek' type='b' access='read'/>
    <property name='CanControl' type='b' access='read'/>
  </interface>
  <interface name='{IFACE_PROPS}'>
    <method name='Get'>
      <arg direction='in' name='interface_name' type='s'/>
      <arg direction='in' name='property_name' type='s'/>
      <arg direction='out' name='value' type='v'/>
    </method>
    <method name='GetAll'>
      <arg direction='in' name='interface_name' type='s'/>
      <arg direction='out' name='properties' type='a{{sv}}'/>
    </method>
    <method name='Set'>
      <arg direction='in' name='interface_name' type='s'/>
      <arg direction='in' name='property_name' type='s'/>
      <arg direction='in' name='value' type='v'/>
    </method>
  </interface>
</node>
"""


def _live():
    """Return the playback module lazily (avoids an import cycle)."""

    import playback

    return playback


class MprisService:
    """Owns the MPRIS bus name and serves requests on a background thread."""

    def __init__(self, identity="EchoYT"):
        self.identity = identity

        self._lock = threading.Lock()
        self._pending_lock = threading.Lock()
        self._pending = {}

        self._stop = threading.Event()
        self._thread = None
        self._conn = None

        self.available = False
        self.error = None

        self._playback_status = "Stopped"
        self._metadata = {}
        self._volume = 1.0
        self._loop = "None"
        self._shuffle = False
        self._rate = 1.0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        if self._thread and self._thread.is_alive():
            return

        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="mpris", daemon=True
        )
        self._thread.start()

    def stop(self):
        self._stop.set()

        if self._thread:
            self._thread.join(timeout=3)

    # ------------------------------------------------------------------
    # Background worker
    # ------------------------------------------------------------------

    def _run(self):
        try:
            conn = open_dbus_connection(bus="SESSION")
        except Exception as e:
            self.error = f"MPRIS unavailable: {e}"
            log.debug(self.error)
            return

        self._conn = conn

        try:
            reply = conn.send_and_get_reply(
                DBus().RequestName(BUS_NAME, 0)
            )
            result = reply.body[0] if reply.body else 0

            if result not in (1, 4):
                self.error = f"MPRIS: could not own {BUS_NAME} (result {result})"
                log.debug(self.error)
                return
        except Exception as e:
            self.error = f"MPRIS setup failed: {e}"
            log.debug(self.error)
            return

        self.available = True

        while not self._stop.is_set():
            self._flush()

            try:
                msg = conn.receive(timeout=0.25)

            except TimeoutError:
                continue

            except Exception:
                break

            try:
                self._dispatch(msg)

            except Exception as e:
                log.debug("MPRIS dispatch error: %s", e)

        try:
            conn.send_and_get_reply(DBus().ReleaseName(BUS_NAME))

        except Exception:
            pass

        try:
            conn.close()

        except Exception:
            pass

        self.available = False

    # ------------------------------------------------------------------
    # Outgoing notifications (called from the app/threads)
    # ------------------------------------------------------------------

    def update_playback_status(self, status):
        with self._lock:
            if status == self._playback_status:
                return
            self._playback_status = status

        self._queue("PlaybackStatus", ("s", status))

    def update_metadata(self, metadata):
        with self._lock:
            self._metadata = metadata

        self._queue("Metadata", ("a{sv}", metadata))

    def update_loop_status(self, status):
        with self._lock:
            self._loop = status

        self._queue("LoopStatus", ("s", status))

    def update_shuffle(self, enabled):
        with self._lock:
            self._shuffle = bool(enabled)

        self._queue("Shuffle", ("b", bool(enabled)))

    def notify_seeked(self, position_us):
        self._send_signal(
            IFACE_PLAYER,
            "Seeked",
            "x",
            (int(position_us),),
        )

    def _current_loop_status(self):
        try:
            return {"one": "Track", "all": "Playlist"}.get(
                _live().get_loop_mode(), "None"
            )

        except Exception:
            with self._lock:
                return self._loop

    def _current_shuffle(self):
        try:
            return bool(_live().is_shuffle())

        except Exception:
            with self._lock:
                return self._shuffle

    def _queue(self, prop, typed_value):
        with self._pending_lock:
            self._pending[prop] = typed_value

    def _flush(self):
        with self._pending_lock:
            if not self._pending:
                return
            changed = self._pending
            self._pending = {}

        self._send_signal(
            IFACE_PROPS,
            "PropertiesChanged",
            "sa{sv}as",
            (IFACE_PLAYER, changed, []),
        )

    def _send_signal(self, interface, name, signature, body):
        if self._conn is None:
            return

        try:
            self._conn.send(
                new_signal(
                    DBusAddress(OBJECT_PATH, interface=interface),
                    name,
                    signature,
                    body,
                )
            )

        except Exception:
            pass

    # ------------------------------------------------------------------
    # Incoming calls
    # ------------------------------------------------------------------

    def _dispatch(self, msg):
        if msg.header.message_type != MessageType.method_call:
            return

        fields = msg.header.fields
        path = fields.get(HeaderFields.path)
        interface = fields.get(HeaderFields.interface)
        member = fields.get(HeaderFields.member)

        if path != OBJECT_PATH:
            self._reply_error(
                msg,
                "org.freedesktop.DBus.Error.UnknownObject",
                f"Unknown object {path}",
            )
            return

        if interface == IFACE_PROPS:
            self._handle_properties(msg, member)

        elif interface == IFACE_PLAYER:
            self._handle_player(msg, member)

        elif interface == IFACE_ROOT:
            self._handle_root(msg, member)

        elif interface == IFACE_INTROSPECT:
            self._reply(msg, "s", (INTROSPECTION_XML,))

        else:
            self._reply_error(
                msg,
                "org.freedesktop.DBus.Error.UnknownInterface",
                f"Unknown interface {interface}",
            )

    def _handle_root(self, msg, member):
        if member in ("Raise", "Quit"):
            self._reply(msg)

        else:
            self._reply_error(
                msg, "org.freedesktop.DBus.Error.UnknownMethod", member
            )

    def _handle_player(self, msg, member):
        try:
            if member in ("Play", "Pause", "PlayPause", "Next", "Previous", "Stop"):
                self._control(member)
                self._reply(msg)

            elif member == "Seek":
                (offset,) = msg.body
                self._seek(offset)
                self._reply(msg)

            elif member == "SetPosition":
                _track, position = msg.body
                self._set_position(position)
                self._reply(msg)

            elif member == "OpenUri":
                self._reply_error(
                    msg,
                    "org.freedesktop.DBus.Error.NotSupported",
                    "OpenUri is not supported",
                )

            else:
                self._reply_error(
                    msg, "org.freedesktop.DBus.Error.UnknownMethod", member
                )

        except Exception as e:
            self._reply_error(
                msg, "org.freedesktop.DBus.Error.Failed", str(e)
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    def _props_for(self, interface):
        if interface == IFACE_ROOT:
            return {
                "CanQuit": ("b", False),
                "CanRaise": ("b", False),
                "HasTrackList": ("b", False),
                "Identity": ("s", self.identity),
                "DesktopEntry": ("s", "echoyt"),
                "SupportedUriSchemes": ("as", []),
                "SupportedMimeTypes": ("as", []),
            }

        if interface == IFACE_PLAYER:
            with self._lock:
                metadata = dict(self._metadata)
                volume = self._volume
                rate = self._rate

            return {
                "PlaybackStatus": ("s", self._status()),
                "LoopStatus": ("s", self._current_loop_status()),
                "Rate": ("d", rate),
                "Shuffle": ("b", self._current_shuffle()),
                "Metadata": ("a{sv}", metadata),
                "Volume": ("d", volume),
                "Position": ("x", self._position()),
                "MinimumRate": ("d", 1.0),
                "MaximumRate": ("d", 1.0),
                "CanGoNext": ("b", True),
                "CanGoPrevious": ("b", True),
                "CanPlay": ("b", True),
                "CanPause": ("b", True),
                "CanSeek": ("b", True),
                "CanControl": ("b", True),
            }

        return None

    def _handle_properties(self, msg, member):
        if member == "Get":
            interface, prop = msg.body
            props = self._props_for(interface)

            if not props or prop not in props:
                self._reply_error(
                    msg,
                    "org.freedesktop.DBus.Error.UnknownProperty",
                    f"Unknown property {prop}",
                )
                return

            self._reply(msg, "v", (props[prop],))

        elif member == "GetAll":
            (interface,) = msg.body
            self._reply(msg, "a{sv}", (self._props_for(interface) or {},))

        elif member == "Set":
            interface, prop, value = msg.body
            self._set_property(interface, prop, value)
            self._reply(msg)

        else:
            self._reply_error(
                msg, "org.freedesktop.DBus.Error.UnknownMethod", member
            )

    def _set_property(self, interface, prop, value):
        if interface != IFACE_PLAYER:
            return

        sig, raw = value

        if prop == "Volume" and sig == "d":
            vol = max(0.0, min(1.0, float(raw)))

            with self._lock:
                self._volume = vol

            try:
                _live().player.volume = vol * 100

            except Exception:
                pass

            self._queue("Volume", ("d", vol))

        elif prop == "LoopStatus" and sig == "s":
            status = raw if raw in ("None", "Track", "Playlist") else "None"

            with self._lock:
                self._loop = status

            try:
                _live().set_loop_mode(
                    {"Track": "one", "Playlist": "all"}.get(status, "off")
                )

            except Exception:
                pass

            self._queue("LoopStatus", ("s", status))

        elif prop == "Shuffle" and sig == "b":
            enabled = bool(raw)

            with self._lock:
                self._shuffle = enabled

            try:
                _live().set_shuffle(enabled)

            except Exception:
                pass

            self._queue("Shuffle", ("b", enabled))

        elif prop == "Rate" and sig == "d":
            with self._lock:
                self._rate = float(raw)

            self._queue("Rate", ("d", float(raw)))

    # ------------------------------------------------------------------
    # Live state
    # ------------------------------------------------------------------

    def _status(self):
        try:
            player = _live().player

            if getattr(player, "path", None) in (None, ""):
                return "Stopped"

            return "Paused" if player.pause else "Playing"

        except Exception:
            with self._lock:
                return self._playback_status

    def _position(self):
        try:
            pos = _live().player.time_pos

            if pos is not None:
                return int(max(0.0, pos) * 1_000_000)

        except Exception:
            pass

        return 0

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------

    def _control(self, action):
        pb = _live()

        if action == "Play":
            if pb.player.pause:
                pb.toggle_pause()

        elif action == "Pause":
            if not pb.player.pause:
                pb.toggle_pause()

        elif action == "PlayPause":
            pb.toggle_pause()

        elif action == "Next":
            pb.next_track()

        elif action == "Previous":
            pb.prev_track()

        elif action == "Stop":
            pb.stop_playback()

        self.update_playback_status(self._status())

    def _seek(self, offset_us):
        try:
            player = _live().player
            target = max(0.0, (player.time_pos or 0.0) + offset_us / 1_000_000)
            player.command("seek", target, "absolute")
            self.notify_seeked(int(target * 1_000_000))

        except Exception:
            pass

    def _set_position(self, position_us):
        try:
            player = _live().player
            target = max(0.0, position_us / 1_000_000)
            player.command("seek", target, "absolute")
            self.notify_seeked(int(target * 1_000_000))

        except Exception:
            pass

    # ------------------------------------------------------------------
    # Reply helpers
    # ------------------------------------------------------------------

    def _reply(self, msg, signature=None, body=()):
        if self._conn is None:
            return

        try:
            if signature is None:
                self._conn.send(new_method_return(msg))

            else:
                self._conn.send(new_method_return(msg, signature, body))

        except Exception:
            pass

    def _reply_error(self, msg, name, message):
        if self._conn is None:
            return

        try:
            self._conn.send(new_error(msg, name, "s", (message,)))

        except Exception:
            pass
