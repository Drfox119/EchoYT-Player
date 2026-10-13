from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Legacy single-playlist file. Migrated into PLAYLISTS_DIR on first run.
PLAYLIST_PATH = BASE_DIR / "playlist.txt"

# Multiple named playlists are stored as one .txt file per playlist.
PLAYLISTS_DIR = BASE_DIR / "playlists"
DEFAULT_PLAYLIST = "Default"

# Local-only secret. Gitignored, created on first run by settings.py.
DISCORD_ID_PATH = BASE_DIR / "discord_app_id.txt"
