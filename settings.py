"""User settings that must never be committed to version control.

Currently this is just the Discord application (client) ID. It is stored in
a plain text file next to the app so the user only has to enter it once.
"""

import json

from config import DISCORD_ID_PATH, BASE_DIR

# Appearance preferences (accent colour + glass look).
THEME_PATH = BASE_DIR / "theme.json"
DEFAULT_ACCENT = "#89b4fa"
DEFAULT_GLASS = True

DEFAULT_DISCORD_INSTRUCTIONS = (
    "Paste your Discord Application ID.\n\n"
    "How to get one:\n"
    "  1. Go to https://discord.com/developers/applications\n"
    "  2. New Application -> give it a name (e.g. EchoYT)\n"
    "  3. Open General Information and copy the 'Application ID'\n\n"
    "It is saved locally in discord_app_id.txt and is never uploaded."
)


def read_discord_app_id():
    """Return the saved Discord App ID, or an empty string if unset."""

    try:
        return DISCORD_ID_PATH.read_text(encoding="utf-8").strip()

    except FileNotFoundError:
        return ""

    except OSError:
        return ""


def save_discord_app_id(app_id: str):
    """Persist the Discord App ID to the local settings file."""

    app_id = (app_id or "").strip()

    DISCORD_ID_PATH.write_text(app_id + "\n", encoding="utf-8")

    return app_id


def read_appearance():
    """Return the saved ``(accent_hex, glass)`` appearance preferences."""

    try:
        data = json.loads(THEME_PATH.read_text(encoding="utf-8"))

    except (FileNotFoundError, OSError, ValueError):
        return DEFAULT_ACCENT, DEFAULT_GLASS

    accent = str(data.get("accent") or DEFAULT_ACCENT)
    glass = bool(data.get("glass", DEFAULT_GLASS))

    return accent, glass


def save_appearance(accent: str, glass: bool):
    """Persist the accent colour and glass preference locally."""

    accent = accent or DEFAULT_ACCENT

    try:
        THEME_PATH.write_text(
            json.dumps({"accent": accent, "glass": bool(glass)}, indent=2),
            encoding="utf-8",
        )

    except OSError:
        pass

    return accent, bool(glass)
