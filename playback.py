import asyncio
import os
import random
import re
import sys
import threading
import time

# On Windows, python-mpv loads libmpv from %PATH% (or next to mpv.py). In a
# frozen build the DLL sits in the bundle directory, so make sure that
# directory is searched *before* importing mpv.
if os.name == "nt":
    _dll_dirs = [os.path.dirname(os.path.abspath(__file__))]

    _meipass = getattr(sys, "_MEIPASS", None)

    if _meipass:
        _dll_dirs.insert(0, _meipass)

    for _dll_dir in _dll_dirs:
        try:
            os.add_dll_directory(_dll_dir)

        except Exception:
            pass

        os.environ["PATH"] = _dll_dir + os.pathsep + os.environ.get("PATH", "")

import mpv
from pypresence import Presence

import playlists
import settings

try:
    import mpris as _mpris
except Exception:
    _mpris = None

YOUTUBE_ID_RE = re.compile(
    r"(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})"
)


def _thumbnail_for_path(path):
    """Return a YouTube thumbnail URL for the current media path, if any."""

    if not path:
        return None

    match = YOUTUBE_ID_RE.search(path)

    if not match:
        return None

    return f"https://i.ytimg.com/vi/{match.group(1)}/hqdefault.jpg"


# ============================================================
# DISCORD
# ============================================================

RPC = None
discord_connected = False


def connect_discord(app_id=None, timeout=5.0):
    """Connect Discord Rich Presence using the saved (or given) App ID.

    Returns True on success. If no App ID is available yet, returns False
    quietly so the app keeps working without Discord.

    ``Presence.connect()`` can block forever when Discord's IPC socket accepts
    the connection but never answers (e.g. a second instance, or Discord stuck
    mid-restart), so the attempt is bounded by ``timeout`` seconds. It also
    must run in a thread that has its own event loop, otherwise pypresence
    deadlocks.
    """

    global RPC, discord_connected

    app_id = (app_id or settings.read_discord_app_id() or "").strip()

    if not app_id:
        discord_connected = False
        return False

    result = {}

    def _attempt():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            presence = Presence(app_id)
            presence.connect()

            result["presence"] = presence

        except Exception as e:
            result["error"] = e

    try:
        worker = threading.Thread(target=_attempt, daemon=True)
        worker.start()
        worker.join(timeout)

        presence = result.get("presence")

        if presence is not None:
            RPC = presence
            discord_connected = True
            print("Discord Rich Presence connected!")
            return True

        RPC = None
        discord_connected = False

        if "error" in result:
            print(f"Discord Rich Presence unavailable: {result['error']}")

        elif worker.is_alive():
            print("Discord Rich Presence timed out; continuing without it.")

        return False

    except Exception as e:
        RPC = None
        discord_connected = False
        print(f"Discord Rich Presence unavailable: {e}")
        return False


def set_discord_app_id(app_id):
    """Save a new App ID and (re)connect with it."""

    settings.save_discord_app_id(app_id)
    disconnect_discord()

    return connect_discord()


def disconnect_discord():
    global RPC, discord_connected

    if RPC is not None:

        try:
            RPC.clear()
            RPC.close()

        except Exception:
            pass

    RPC = None
    discord_connected = False


connect_discord()


def update_discord(title, paused=False):

    if not discord_connected or RPC is None:
        return

    presence = {
        "details": "EchoYT",
        "state": f"Paused: {title}" if paused else f"Listening: {title}",
        "large_text": title,
    }

    try:
        thumbnail = _thumbnail_for_path(player.path)
    except Exception:
        thumbnail = None

    if thumbnail:
        presence["large_image"] = thumbnail

    try:
        RPC.update(**presence)

    except Exception as e:
        print(f"Discord update failed: {e}")


# ============================================================
# MPV
# ============================================================

player = mpv.MPV(
    ytdl=True,
    input_default_bindings=True,
    video=False
)


# ============================================================
# MPRIS (desktop media integration)
# ============================================================
#
# A pure-Python MPRIS service lets the desktop (media keys, "now playing"
# widgets, playerctl) see and control playback. The native mpv-mpris plugin
# cannot be used here because loading it into this Qt process crashes.

mpris_service = None

if _mpris is not None:

    try:
        mpris_service = _mpris.MprisService()
        mpris_service.start()

    except Exception as e:
        mpris_service = None
        print(f"MPRIS unavailable: {e}")


def _mpris_status():

    try:
        if getattr(player, "path", None) in (None, ""):
            return "Stopped"

        return "Paused" if player.pause else "Playing"

    except Exception:
        return "Stopped"


def _mpris_metadata(title, path):

    key = path or title or "unknown"
    safe = re.sub(r"[^A-Za-z0-9_]", "_", str(key))

    if not safe or safe[0].isdigit():
        safe = "t_" + safe

    metadata = {
        "mpris:trackid": ("o", f"{_mpris.TRACK_PATH_BASE}{safe}"),
    }

    if title:
        metadata["xesam:title"] = ("s", title)

    if path:
        metadata["xesam:url"] = ("s", path)

    thumbnail = _thumbnail_for_path(path)

    if thumbnail:
        metadata["mpris:artUrl"] = ("s", thumbnail)

    try:
        duration = player.duration

        if duration:
            metadata["mpris:length"] = ("x", int(duration * 1_000_000))

    except Exception:
        pass

    return metadata


def _update_mpris(title=None, path=None):

    if mpris_service is None:
        return

    title = player.media_title if title is None else title
    path = player.path if path is None else path

    try:
        mpris_service.update_metadata(_mpris_metadata(title, path))
        mpris_service.update_playback_status(_mpris_status())

    except Exception:
        pass


# ============================================================
# WATCH MPV TITLE
# ============================================================

@player.property_observer("media-title")
def media_title_changed(name, value):

    if value:

        print(f"\nNow playing: {value}")

        update_discord(value)

    _update_mpris(value, player.path)


@player.property_observer("pause")
def pause_changed(name, value):

    if mpris_service is not None:
        mpris_service.update_playback_status(_mpris_status())


@player.property_observer("duration")
def duration_changed(name, value):

    # Duration is unknown when the title first changes; refresh metadata once
    # it is available so MPRIS clients get mpris:length.
    if value:
        _update_mpris()


# ============================================================
# REUSABLE PLAYER HELPERS (used by the GUI and the CLI)
# ============================================================

def load_playlist_items(playlist=None):
    """Return a playlist as a list of {"url", "title"} dicts."""

    return playlists.load_items(playlist)


def write_playlist(entries, playlist=None):
    """Rewrite a playlist from a list of {"url", "title"} dicts."""

    playlists.save_items(entries, playlist)


def load_playlist(playlist=None):
    """Return the list of URLs in a playlist."""

    return [entry["url"] for entry in load_playlist_items(playlist)]


def play_playlist(playlist=None):
    """(Re)load a playlist into MPV and start playing.

    Returns the number of tracks queued.
    """

    urls = load_playlist(playlist)

    if not urls:
        return 0

    player.command("stop")

    player.playlist_clear()

    for link in urls:
        player.playlist_append(link)

    _wait_playlist_count(len(urls))

    global _natural_order
    _natural_order = [entry["id"] for entry in _playlist_entries()]

    if _shuffle_on:
        _shuffle_now(keep_current=False)

    player.playlist_pos = 0
    player.pause = False

    return len(urls)


def toggle_pause():
    """Toggle playback and keep Discord in sync. Returns True when paused."""

    player.pause = not player.pause

    title = player.media_title or "Unknown song"

    update_discord(title, paused=player.pause)

    if mpris_service is not None:
        mpris_service.update_playback_status(_mpris_status())

    return player.pause


def next_track():
    player.command("playlist-next", "weak")


def prev_track():
    player.command("playlist-prev", "weak")


# ============================================================
# SHUFFLE / LOOP
# ============================================================

LOOP_MODES = ("off", "all", "one")

# mpv only applies its own "shuffle" option when a playlist is loaded, so toggling
# it mid-playback does nothing. Instead we reorder the live playlist ourselves
# with playlist-move commands.
_shuffle_on = False
_natural_order = []  # playlist entry ids in the order the playlist was loaded


def _playlist_entries():
    try:
        return list(player.playlist)

    except Exception:
        return []


def _wait_playlist_count(count, timeout=1.0):
    """Wait until mpv reports ``count`` playlist entries (best effort)."""

    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            if player.playlist_count >= count:
                return

        except Exception:
            pass

        time.sleep(0.01)


def _reorder_to(target_ids):
    """Realize ``target_ids`` by moving playlist entries into place."""

    for target_index, entry_id in enumerate(target_ids):
        index = None

        for i, entry in enumerate(_playlist_entries()):
            if entry.get("id") == entry_id:
                index = i
                break

        if index is None or index == target_index:
            continue

        player.command("playlist-move", str(index), str(target_index))


def _shuffle_now(keep_current=True):
    """Randomize the playlist order, optionally keeping the playing track first."""

    entries = _playlist_entries()

    if len(entries) < 2:
        return

    ids = [entry["id"] for entry in entries]

    if keep_current:
        pos = player.playlist_pos
        current = None

        if pos is not None and 0 <= pos < len(entries):
            current = entries[pos]["id"]

        rest = [i for i in ids if i != current]
        random.shuffle(rest)
        target = ([current] if current is not None else []) + rest

    else:
        random.shuffle(ids)
        target = ids

    _reorder_to(target)


def _restore_natural_order():
    entries = _playlist_entries()

    if not _natural_order:
        return

    if {entry.get("id") for entry in entries} == set(_natural_order):
        _reorder_to(_natural_order)


def set_shuffle(enabled):
    """Turn playlist shuffle on or off. Returns the new state."""

    global _shuffle_on

    enabled = bool(enabled)
    _shuffle_on = enabled

    if enabled:
        _shuffle_now(keep_current=True)

    else:
        _restore_natural_order()

    if mpris_service is not None:
        mpris_service.update_shuffle(enabled)

    return enabled


def is_shuffle():
    return _shuffle_on


def set_loop_mode(mode):
    """Set the loop mode: ``off``, ``all`` (playlist) or ``one`` (track)."""

    mode = (mode or "off").lower()

    if mode not in LOOP_MODES:
        mode = "off"

    if mode == "all":
        player.loop_playlist = "inf"
        player.loop_file = "no"

    elif mode == "one":
        player.loop_playlist = "no"
        player.loop_file = "inf"

    else:
        player.loop_playlist = "no"
        player.loop_file = "no"

    if mpris_service is not None:
        mpris_service.update_loop_status(_mpris_loop_status())

    return mode


def get_loop_mode():
    """Return the current loop mode: ``off``, ``all`` or ``one``."""

    try:
        playlist_loop = player.loop_playlist
        file_loop = player.loop_file

    except Exception:
        return "off"

    if file_loop in ("inf", "force"):
        return "one"

    if playlist_loop in ("inf", "force"):
        return "all"

    return "off"


def _mpris_loop_status():
    return {"one": "Track", "all": "Playlist"}.get(get_loop_mode(), "None")


def stop_playback():
    player.command("stop")

    if mpris_service is not None:
        mpris_service.update_playback_status("Stopped")


def seek(seconds):
    """Seek to an absolute position (in seconds) of the current track."""

    try:
        seconds = max(0.0, float(seconds))
        player.command("seek", str(seconds), "absolute")

    except Exception:
        return False

    if mpris_service is not None:
        try:
            mpris_service.notify_seeked(int(seconds * 1_000_000))

        except Exception:
            pass

    return True


def shutdown():
    """Release MPV, MPRIS and Discord resources."""

    disconnect_discord()

    if mpris_service is not None:
        mpris_service.stop()

    try:
        player.terminate()

    except Exception:
        pass


# ============================================================
# PLAYER
# ============================================================

def new():

    playlist = load_playlist()

    if not playlist:

        print("Playlist is empty!")
        return


    print(f"Adding {len(playlist)} track(s) to MPV queue...")


    for link in playlist:
        player.playlist_append(link)


    player.playlist_pos = 0


    print("\n--- CONTROLS ---")
    print("p: Pause/Play | n: Next | b: Back | q: Quit\n")


    while True:

        try:

            cmd = input("Command [p/n/b/q]: ").strip().lower()


            # -------------------------
            # PAUSE / PLAY
            # -------------------------

            if cmd == "p":

                player.pause = not player.pause

                status = "Paused" if player.pause else "Playing"

                print(f"[{status}]")

                title = player.media_title or "Unknown song"

                update_discord(
                    title,
                    paused=player.pause
                )


            # -------------------------
            # NEXT
            # -------------------------

            elif cmd == "n":

                print("Skipping to NEXT track...")

                player.command(
                    "playlist-next",
                    "weak"
                )


            # -------------------------
            # PREVIOUS
            # -------------------------

            elif cmd == "b":

                print("Going BACK to previous track...")

                player.command(
                    "playlist-prev",
                    "weak"
                )


            # -------------------------
            # QUIT
            # -------------------------

            elif cmd == "q":

                print("Stopping player...")

                if discord_connected:

                    try:
                        RPC.clear()

                    except Exception:
                        pass

                player.terminate()

                break


        except Exception as e:

            print(f"Command error: {e}")


if __name__ == "__main__":
    new()