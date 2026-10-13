# EchoYT

A lightweight **desktop YouTube playlist player** with a modern dark GUI.
Search YouTube, build multiple playlists, and play them through `mpv` while
showing what you're listening to on Discord (Rich Presence).

No YouTube API key required — search is powered by `yt-dlp`.

---

## Features

* **Modern PySide6 GUI** — dark theme, sidebar navigation, responsive layout.
* **Search YouTube without an API key** — powered by `yt-dlp`.
* **Multiple playlists** — create, switch, and delete named playlists.
* **No duplicate tracks** — the same song can't be added to a playlist twice.
* **Song names, not URLs** — titles are stored and shown; missing ones are
  resolved automatically in the background.
* **Playback via mpv** — play / pause, next / previous, stop, volume, seek bar.
* **Discord Rich Presence** — shows `Listening: <song>` with the song's banner.
  Uses **your own** Discord Application ID, entered once and saved locally.
* **Desktop media integration (MPRIS)** — media keys, "now playing" widgets
  (e.g. Waybar, GNOME, KDE) and `playerctl` can see and control playback.
* **Still scriptable** — `Main.py` keeps the original command-line interface.

---

## Requirements

* Python 3.10+
* The **mpv** media player must be installed on your system
  (`sudo apt install mpv`, `sudo pacman -S mpv`, `brew install mpv`, ...).

Python packages:

```bash
pip install -r requirements.txt
```

---

## Run the GUI

```bash
python -m gui
```

> Run it from the project folder. Playlists are stored in `playlists/`.

## Run the CLI

```bash
python Main.py
```

---

## Discord Rich Presence (optional)

Rich Presence is **off until you add your own Discord Application ID**.

1. Go to <https://discord.com/developers/applications> and click **New Application**.
2. Open **General Information** and copy the **Application ID**.
3. Launch the app — on first run it asks for the ID, or add it later under
   **Settings** in the sidebar.

The ID is saved in `discord_app_id.txt` (gitignored) so you only enter it once.
No secrets are stored in the source code.

---

## Desktop media integration / MPRIS (Linux, optional)

On Linux the player exposes a standard **MPRIS** interface, so desktop media
keys, "now playing" widgets and `playerctl` can see and control playback:

```bash
playerctl -l            # lists "echoyt"
playerctl metadata      # title, artist, artwork, length
playerctl play-pause    # controls EchoYT
```

This is implemented in pure Python (`mpris.py`) via the `jeepney` library.
If `jeepney` isn't installed the app still runs normally — the MPRIS
integration is simply disabled. It is **not** the native `mpv-mpris` plugin:
loading that into the Qt process crashes, so it is intentionally avoided.

---

## Project layout

```
Main.py        CLI entry point
newsongs.py    YouTube search (yt-dlp) and adding tracks
playback.py    mpv player + Discord Rich Presence + MPRIS hookup
mpris.py       pure-Python MPRIS D-Bus service (Linux desktop integration)
playlists.py   named playlist storage (create / remove / dedupe)
settings.py    local user settings (Discord App ID)
config.py      paths and constants
gui/           PySide6 desktop interface
  theme.py       dark theme / stylesheet
  workers.py     background threads (search, title lookup)
  main_window.py sidebar, Add Songs, Player and Settings pages
```
