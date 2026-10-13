import re

import mpv
from pypresence import Presence

import playlists
import settings

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


def connect_discord(app_id=None):
    """Connect Discord Rich Presence using the saved (or given) App ID.

    Returns True on success. If no App ID is available yet, returns False
    quietly so the app keeps working without Discord.
    """

    global RPC, discord_connected

    app_id = (app_id or settings.read_discord_app_id() or "").strip()

    if not app_id:
        discord_connected = False
        return False

    try:
        RPC = Presence(app_id)
        RPC.connect()
        discord_connected = True
        print("Discord Rich Presence connected!")
        return True

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
# WATCH MPV TITLE
# ============================================================

@player.property_observer("media-title")
def media_title_changed(name, value):

    if value:

        print(f"\nNow playing: {value}")

        update_discord(value)


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

    return player.pause


def next_track():
    player.command("playlist-next", "weak")


def prev_track():
    player.command("playlist-prev", "weak")


def stop_playback():
    player.command("stop")


def shutdown():
    """Release MPV and Discord resources."""

    disconnect_discord()

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