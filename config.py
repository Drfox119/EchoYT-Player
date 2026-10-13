import os
import sys
from pathlib import Path


def _user_data_dir() -> Path:
    """Return a per-user directory for playlists and settings.

    Used when running from a frozen build (PyInstaller), where the application
    bundle is read-only and ``__file__`` points into a temporary extraction
    directory that is wiped between runs.
    """

    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"

    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"

    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"

    return Path(base) / "EchoYT"


if getattr(sys, "frozen", False):
    BASE_DIR = _user_data_dir()

else:
    # Running from source: keep everything next to the project files.
    BASE_DIR = Path(__file__).resolve().parent

BASE_DIR.mkdir(parents=True, exist_ok=True)

# Legacy single-playlist file. Migrated into PLAYLISTS_DIR on first run.
PLAYLIST_PATH = BASE_DIR / "playlist.txt"

# Multiple named playlists are stored as one .txt file per playlist.
PLAYLISTS_DIR = BASE_DIR / "playlists"
DEFAULT_PLAYLIST = "Default"

# Local-only secret. Gitignored, created on first run by settings.py.
DISCORD_ID_PATH = BASE_DIR / "discord_app_id.txt"
