"""User settings that must never be committed to version control.

Currently this is just the Discord application (client) ID. It is stored in
a plain text file next to the app so the user only has to enter it once.
"""

from config import DISCORD_ID_PATH

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
