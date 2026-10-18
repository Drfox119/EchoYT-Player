# EchoYT

A lightweight **desktop YouTube playlist player** with a modern dark GUI.
Search YouTube, build multiple playlists, and play them through `mpv` while
showing what you're listening to on Discord (Rich Presence).
the search is powered by `yt-dlp`.

## Project Perview
<img width="1910" height="1032" alt="EhcoYt" src="https://github.com/user-attachments/assets/5ee5abc7-043f-4b27-9dab-7b4c125249a9" />

---

## Download

Prebuilt standalone builds are published on the
[**Releases**](https://github.com/Drfox119/EchoYT-Player/releases) page:

* **Windows** — `EchoYT-windows-x86_64.zip` (unzip and run `EchoYT.exe`).
* **Linux** — `EchoYT-linux-x86_64.tar.gz` (extract and run `./EchoYT`).

No Python installation is needed for the prebuilt builds.

---

## Features

* **Modern PySide6 GUI** — dark theme, sidebar navigation, responsive layout.
* **Search YouTube without an API key** — powered by `yt-dlp`.
* **Multiple playlists** — create, switch, and delete named playlists.
* **No duplicate tracks** — the same song can't be added to a playlist twice.
* **Playback via mpv** — play / pause, next / previous, stop, volume, seek bar.
* **Discord Rich Presence** — shows `Listening: <song>` with the song's banner.
  Uses **your own** Discord Application ID, entered once and saved locally.
* **Desktop media integration (MPRIS)** — media keys, "now playing" widgets
  (e.g. Waybar, GNOME, KDE) and `playerctl` can see and control playback.
* **Different themes you can choose From**
* Blue: <img width="1912" height="1035" alt="1" src="https://github.com/user-attachments/assets/e7cdbe0a-9e42-44be-8421-8feac5a08029" />
* light blue: <img width="1919" height="1041" alt="2" src="https://github.com/user-attachments/assets/afee95ff-1728-4556-a158-d509414680be" />
* cyan: <img width="1919" height="1035" alt="3" src="https://github.com/user-attachments/assets/d3443e0a-e225-4783-99d1-e82fbb44c2c5" />
* lime: <img width="1918" height="1038" alt="4" src="https://github.com/user-attachments/assets/89bef538-46db-45aa-84d1-bf4f589ecf0e" />



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

## Build a standalone app

You can build a self-contained executable with
[PyInstaller](https://pyinstaller.org):

```bash
pip install -r requirements-build.txt
pyinstaller --noconfirm --clean echoyt.spec
```

The result is `dist/EchoYT/` (a folder build). Run `EchoYT`/`EchoYT.exe`.

* **Windows** — put `libmpv-2.dll` next to `echoyt.spec` before building so it
  gets bundled (the `packaging/get_libmpv.py` helper downloads one). It is
  shipped in the Windows release.
* **Linux** — the app uses your system `libmpv`, so install `mpv`/`libmpv`
  (e.g. `sudo apt install libmpv2`).

Pushing a tag like `v1.0.0` triggers [`.github/workflows/release.yml`], which
builds both platforms and publishes them to the Releases page.

> In a built app, playlists and the Discord App ID are stored per-user
> (`%APPDATA%\EchoYT` on Windows, `~/.local/share/EchoYT` on Linux) so they
> survive upgrades. Running from source keeps using the project folder.

---

## Project layout

```
Main.py        CLI entry point
echoyt.py      GUI entry point for builds (wraps `python -m gui`)
echoyt.spec    PyInstaller build spec
newsongs.py    YouTube search (yt-dlp) and adding tracks
playback.py    mpv player + Discord Rich Presence + MPRIS hookup
mpris.py       pure-Python MPRIS D-Bus service (Linux desktop integration)
playlists.py   named playlist storage (create / remove / dedupe)
settings.py    local user settings (Discord App ID)
config.py      paths and constants
packaging/     build helpers (Windows libmpv downloader)
gui/           PySide6 desktop interface
  theme.py       dark theme / stylesheet
  workers.py     background threads (search, title lookup)
  main_window.py sidebar, Add Songs, Player and Settings pages
```
