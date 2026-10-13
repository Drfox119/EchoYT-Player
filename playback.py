import re
import threading

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


def connect_discord(app_id=None, timeout=3.0):
    """Connect Discord Rich Presence using the saved (or given) App ID.

    Returns True on success. If no App ID is available yet, returns False
    quietly so the app keeps working without Discord.

    ``Presence.connect()`` can block forever when Discord's IPC socket accepts
    the connection but never answers (e.g. a second instance, or Discord stuck
    mid-restart), so the attempt is bounded by ``timeout`` seconds.
    """

    global RPC, discord_connected

    app_id = (app_id or settings.read_discord_app_id() or "").strip()

    if not app_id:
        discord_connected = False
        return False

    presence = None
    result = {}

    try:
        presence = Presence(app_id)

        def _attempt():
            try:
                presence.connect()
                result["ok"] = True

            except Exception as e:
                result["error"] = e

        worker = threading.Thread(target=_attempt, daemon=True)
        worker.start()
        worker.join(timeout)

        if result.get("ok"):
            RPC = presence
            discord_connected = True
            print("Discord Rich Presence connected!")
            return True

        try:
            presence.close()

        except Exception:
            pass

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


def stop_playback():
    player.command("stop")

    if mpris_service is not None:
        mpris_service.update_playback_status("Stopped")


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