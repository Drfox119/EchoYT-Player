"""Named playlist storage.

Each playlist is a plain-text file inside config.PLAYLISTS_DIR. A line is
either ``url`` or ``url<TAB>title``. This module is pure storage: it has no
dependency on mpv, Discord or the GUI.
"""

import re

from config import BASE_DIR, DEFAULT_PLAYLIST, PLAYLISTS_DIR

_UNSAFE = re.compile(r"[^A-Za-z0-9 _-]")


# ============================================================
# PATH / NAME HELPERS
# ============================================================

def safe_name(name):
    """Validate and normalise a playlist name for use as a filename."""

    name = (name or "").strip()

    if not name:
        raise ValueError("Playlist name cannot be empty.")

    cleaned = _UNSAFE.sub("", name).strip()

    if not cleaned:
        raise ValueError("Playlist name must contain letters or numbers.")

    return cleaned


def _path(name):
    return PLAYLISTS_DIR / f"{name}.txt"


# ============================================================
# STORAGE / MIGRATION
# ============================================================

def _migrate_legacy():
    """Move an old single playlist.txt into the Default playlist."""

    legacy = BASE_DIR / "playlist.txt"

    if not legacy.exists():
        return

    default = _path(DEFAULT_PLAYLIST)

    if default.exists():
        return

    try:
        legacy.replace(default)  # move (same filesystem)

    except Exception:  # pragma: no cover - cross-device fallback
        default.write_text(legacy.read_text())
        legacy.unlink()


def ensure_storage():
    PLAYLISTS_DIR.mkdir(parents=True, exist_ok=True)
    _migrate_legacy()

    default = _path(DEFAULT_PLAYLIST)

    if not default.exists():
        default.touch()


# ============================================================
# PLAYLIST MANAGEMENT
# ============================================================

def list_playlists():
    """Return all playlist names, with the Default playlist first."""

    ensure_storage()

    names = sorted(path.stem for path in PLAYLISTS_DIR.glob("*.txt"))

    if DEFAULT_PLAYLIST in names:
        names.remove(DEFAULT_PLAYLIST)
        names.insert(0, DEFAULT_PLAYLIST)

    return names


def create_playlist(name):
    ensure_storage()

    cleaned = safe_name(name)
    path = _path(cleaned)

    if path.exists():
        raise FileExistsError(f"Playlist '{cleaned}' already exists.")

    path.touch()
    return cleaned


def remove_playlist(name):
    ensure_storage()

    cleaned = safe_name(name)
    path = _path(cleaned)

    if not path.exists():
        raise FileNotFoundError(f"Playlist '{cleaned}' does not exist.")

    path.unlink()


# ============================================================
# ENTRY (DE)SERIALISATION
# ============================================================

def _split_entry(line):
    """Parse one playlist line into (url, title). title may be None."""

    line = line.strip()

    if not line:
        return None

    if "\t" in line:
        url, title = line.split("\t", 1)
        return url.strip(), (title.strip() or None)

    return line, None


def load_items(name=None):
    """Return the playlist as a list of {"url", "title"} dicts."""

    ensure_storage()

    path = _path(safe_name(name or DEFAULT_PLAYLIST))
    entries = []

    try:
        with open(path, "r") as file:

            for line in file:

                parsed = _split_entry(line)

                if parsed:
                    entries.append({"url": parsed[0], "title": parsed[1]})

    except FileNotFoundError:
        return []

    return entries


def save_items(entries, name=None):
    """Rewrite a playlist file from a list of {"url", "title"} dicts."""

    ensure_storage()

    path = _path(safe_name(name or DEFAULT_PLAYLIST))

    with open(path, "w") as file:

        for entry in entries:

            title = (entry.get("title") or "").replace("\t", " ").strip()

            if title:
                file.write(f"{entry['url']}\t{title}\n")
            else:
                file.write(f"{entry['url']}\n")


# ============================================================
# MUTATIONS
# ============================================================

def contains(url, name=None):
    return any(entry["url"] == url for entry in load_items(name))


def add_item(url, title=None, name=None):
    """Append a track unless it is already present.

    Returns True when added, False when it was a duplicate.
    """

    entries = load_items(name)

    if any(entry["url"] == url for entry in entries):
        return False

    entries.append({"url": url, "title": title})
    save_items(entries, name)

    return True


def remove_item(url, name=None):
    """Remove a track by URL. Returns True when something was removed."""

    entries = load_items(name)
    remaining = [entry for entry in entries if entry["url"] != url]

    if len(remaining) == len(entries):
        return False

    save_items(remaining, name)

    return True
