"""Main window: sidebar navigation with the Add Songs and Player pages."""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

import newsongs
import playlists
import settings
from gui.workers import SearchWorker, TitleWorker

try:
    import playback

    PLAYBACK = playback
    PLAYBACK_ERROR = ""
except Exception as exc:  # mpv / pypresence unavailable
    PLAYBACK = None
    PLAYBACK_ERROR = str(exc)


def _fmt_time(seconds):
    """Format a number of seconds as mm:ss."""

    if seconds is None:
        return "00:00"

    total = max(0, int(seconds))
    minutes, secs = divmod(total, 60)

    return f"{minutes:02d}:{secs:02d}"


def _set_status(label, text, state="info"):
    label.setText(text)
    label.setProperty("state", state)
    # Re-apply the stylesheet so the [state=...] selector takes effect.
    label.style().unpolish(label)
    label.style().polish(label)


class AddSongPage(QWidget):
    """Search YouTube and add tracks to the playlist."""

    playlistChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.worker = None
        self.active_playlist = None

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(14)

        title = QLabel("Add Songs")
        title.setObjectName("PageTitle")

        self.subtitle = QLabel("Search YouTube and add tracks to a playlist.")
        self.subtitle.setObjectName("PageSubtitle")

        root.addWidget(title)
        root.addWidget(self.subtitle)
        root.addSpacing(6)

        # ---- search row -------------------------------------------------
        search_row = QHBoxLayout()
        search_row.setSpacing(10)

        self.query_edit = QLineEdit()
        self.query_edit.setPlaceholderText("Song or video name...")
        self.query_edit.returnPressed.connect(self.start_search)

        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 25)
        self.count_spin.setValue(5)
        self.count_spin.setSuffix(" results")
        self.count_spin.setFixedWidth(120)

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("Primary")
        self.search_btn.clicked.connect(self.start_search)

        search_row.addWidget(self.query_edit, 1)
        search_row.addWidget(self.count_spin)
        search_row.addWidget(self.search_btn)

        root.addLayout(search_row)

        # ---- progress + status -----------------------------------------
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # indeterminate
        self.progress.setFixedHeight(8)
        self.progress.hide()

        self.status = QLabel("")
        self.status.setObjectName("Status")
        self.status.setWordWrap(True)

        root.addWidget(self.progress)
        root.addWidget(self.status)

        # ---- results ----------------------------------------------------
        results_label = QLabel("RESULTS")
        results_label.setObjectName("SectionLabel")

        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(self._add_current)
        self.results.itemSelectionChanged.connect(self._sync_add_button)

        self.add_btn = QPushButton("Add Selected to Playlist")
        self.add_btn.setObjectName("Primary")
        self.add_btn.setEnabled(False)
        self.add_btn.clicked.connect(self.add_selected)

        root.addWidget(results_label)
        root.addWidget(self.results, 1)
        root.addWidget(self.add_btn)

        # ---- direct URL -------------------------------------------------
        url_label = QLabel("ADD BY URL")
        url_label.setObjectName("SectionLabel")

        url_row = QHBoxLayout()
        url_row.setSpacing(10)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://www.youtube.com/watch?v=...")
        self.url_edit.returnPressed.connect(self.add_url)

        add_url_btn = QPushButton("Add URL")
        add_url_btn.clicked.connect(self.add_url)

        url_row.addWidget(self.url_edit, 1)
        url_row.addWidget(add_url_btn)

        root.addWidget(url_label)
        root.addLayout(url_row)

    # ------------------------------------------------------------------ #
    # Search
    # ------------------------------------------------------------------ #

    def start_search(self):
        if self.worker is not None and self.worker.isRunning():
            return

        query = self.query_edit.text().strip()

        if not query:
            _set_status(self.status, "Enter a song or video name to search.", "error")
            return

        self.results.clear()
        self._set_busy(True)
        _set_status(self.status, f"Searching for '{query}'...", "busy")

        self.worker = SearchWorker(query, self.count_spin.value(), self)
        self.worker.succeeded.connect(self._on_results)
        self.worker.failed.connect(self._on_failed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_results(self, results):
        for video in results:
            item = QListWidgetItem(video["title"])
            item.setToolTip(video["url"])
            item.setData(Qt.UserRole, video)
            self.results.addItem(item)

        _set_status(
            self.status,
            f"Found {len(results)} result(s). Select one and add it to the playlist.",
            "ok",
        )

    def _on_failed(self, message):
        _set_status(self.status, message, "error")

    def _on_worker_finished(self):
        self._set_busy(False)
        self.worker = None

    def _set_busy(self, busy):
        self.progress.setVisible(busy)
        self.search_btn.setEnabled(not busy)
        self.search_btn.setText("Searching..." if busy else "Search")
        self.query_edit.setEnabled(not busy)
        self.count_spin.setEnabled(not busy)

    def stop_search(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(3000)

    # ------------------------------------------------------------------ #
    # Adding tracks
    # ------------------------------------------------------------------ #

    def _sync_add_button(self):
        self.add_btn.setEnabled(bool(self.results.selectedItems()))

    def _add_current(self, _item):
        self.add_selected()

    def add_selected(self):
        items = self.results.selectedItems()

        if not items:
            _set_status(self.status, "Select at least one result first.", "error")
            return

        added = 0
        duplicates = 0

        for item in items:
            video = item.data(Qt.UserRole)

            if not video:
                continue

            if newsongs.add_to_playlist(
                video["url"], video.get("title"), self.active_playlist
            ):
                added += 1
            else:
                duplicates += 1

        if added or duplicates:
            parts = []

            if added:
                parts.append(f"Added {added} track(s)")

            if duplicates:
                parts.append(f"{duplicates} already in playlist")

            state = "ok" if added else "busy"
            _set_status(self.status, " to ".join(parts) + ".", state)

        if added:
            self.playlistChanged.emit()

    def add_url(self):
        url = self.url_edit.text().strip()

        if not url:
            _set_status(self.status, "Paste a URL to add.", "error")
            return

        if not url.lower().startswith(("http://", "https://")):
            _set_status(self.status, "That does not look like a valid URL.", "error")
            return

        if newsongs.add_to_playlist(url, None, self.active_playlist):
            self.url_edit.clear()
            _set_status(self.status, "URL added to the playlist.", "ok")
            self.playlistChanged.emit()
        else:
            _set_status(self.status, "That URL is already in the playlist.", "busy")

    def set_active_playlist(self, name):
        self.active_playlist = name
        self.subtitle.setText(f"Search YouTube and add tracks to '{name}'.")


class PlayerPage(QWidget):
    """Control MPV playback of the playlist."""

    def __init__(self, playback_module, parent=None):
        super().__init__(parent)

        self.playback = playback_module
        self.active_playlist = None
        self._playlist_len = -1
        self._items = []
        self._title_worker = None
        self._attempted_titles = set()

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(14)

        title = QLabel("Player")
        title.setObjectName("PageTitle")

        subtitle = QLabel("Control the currently loaded playlist.")
        subtitle.setObjectName("PageSubtitle")

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(6)

        # ---- now playing ------------------------------------------------
        self.now_label = QLabel("Nothing playing")
        self.now_label.setObjectName("NowPlaying")
        self.now_label.setWordWrap(True)
        root.addWidget(self.now_label)

        self.track_label = QLabel("")
        self.track_label.setObjectName("PageSubtitle")
        root.addWidget(self.track_label)

        # ---- progress ---------------------------------------------------
        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)

        self.elapsed = QLabel("00:00")
        self.elapsed.setObjectName("TimeLabel")
        self.duration = QLabel("00:00")
        self.duration.setObjectName("TimeLabel")

        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)

        progress_row.addWidget(self.elapsed)
        progress_row.addWidget(self.progress, 1)
        progress_row.addWidget(self.duration)

        root.addLayout(progress_row)

        # ---- transport --------------------------------------------------
        controls = QHBoxLayout()
        controls.setSpacing(16)
        controls.addStretch(1)

        self.prev_btn = QPushButton("\u23ee")
        self.prev_btn.setObjectName("Transport")
        self.prev_btn.setToolTip("Previous (b)")
        self.prev_btn.clicked.connect(self._prev)

        self.play_btn = QPushButton("\u25b6")
        self.play_btn.setObjectName("TransportPrimary")
        self.play_btn.setToolTip("Pause / Play (p)")
        self.play_btn.clicked.connect(self._toggle)

        self.next_btn = QPushButton("\u23ed")
        self.next_btn.setObjectName("Transport")
        self.next_btn.setToolTip("Next (n)")
        self.next_btn.clicked.connect(self._next)

        self.stop_btn = QPushButton("\u23f9")
        self.stop_btn.setObjectName("Transport")
        self.stop_btn.setToolTip("Stop (q)")
        self.stop_btn.clicked.connect(self._stop)

        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.next_btn)
        controls.addWidget(self.stop_btn)
        controls.addStretch(1)

        root.addLayout(controls)

        # ---- volume -----------------------------------------------------
        volume_row = QHBoxLayout()
        volume_row.setSpacing(10)

        volume_icon = QLabel("\U0001f50a")
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(100)
        self.volume.setFixedWidth(200)
        self.volume.valueChanged.connect(self._set_volume)

        volume_row.addStretch(1)
        volume_row.addWidget(volume_icon)
        volume_row.addWidget(self.volume)
        volume_row.addStretch(1)

        root.addLayout(volume_row)
        root.addSpacing(6)

        # ---- playlist ---------------------------------------------------
        self.playlist_label = QLabel("PLAYLIST")
        self.playlist_label.setObjectName("SectionLabel")

        self.playlist = QListWidget()
        self.playlist.setObjectName("PlaylistView")
        self.playlist.itemDoubleClicked.connect(self._play_index)

        play_btn = QPushButton("Load & Play Playlist")
        play_btn.setObjectName("Primary")
        play_btn.clicked.connect(self.load_and_play)

        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.setToolTip("Remove the selected track(s) from this playlist")
        self.remove_btn.clicked.connect(self.remove_selected)

        buttons = QHBoxLayout()
        buttons.setSpacing(10)
        buttons.addWidget(play_btn, 1)
        buttons.addWidget(self.remove_btn)

        root.addWidget(self.playlist_label)
        root.addWidget(self.playlist, 1)
        root.addLayout(buttons)

        if self.playback is None:
            for widget in (
                self.prev_btn,
                self.play_btn,
                self.next_btn,
                self.stop_btn,
                play_btn,
                self.volume,
            ):
                widget.setEnabled(False)

            _set_status(
                self.now_label,
                "Playback engine unavailable: " + PLAYBACK_ERROR,
                "error",
            )

        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

        self.refresh_playlist()

    # ------------------------------------------------------------------ #
    # Playlist handling
    # ------------------------------------------------------------------ #

    def set_active_playlist(self, name):
        self.active_playlist = name
        self._playlist_len = -1
        self.playlist_label.setText(f"PLAYLIST  -  {name}".upper())
        self.refresh_playlist(force=True)

    def refresh_playlist(self, force=False):
        if self.playback is None:
            return

        items = self.playback.load_playlist_items(self.active_playlist)

        if not force and len(items) == self._playlist_len:
            return

        self._playlist_len = len(items)
        self._items = items
        self.playlist.clear()

        missing = []

        for entry in items:
            self.playlist.addItem(QListWidgetItem(self._display_name(entry)))

            if not entry["title"]:
                missing.append(entry["url"])

        self._resolve_missing(missing)

    @staticmethod
    def _display_name(entry):
        return entry["title"] or "Unknown track"

    def _resolve_missing(self, urls):
        pending = [url for url in urls if url not in self._attempted_titles]

        if not pending or self._title_worker is not None:
            return

        self._attempted_titles.update(pending)

        self._title_worker = TitleWorker(pending, self)
        self._title_worker.resolved.connect(self._on_titles_resolved)
        self._title_worker.finished.connect(self._on_titles_done)
        self._title_worker.start()

    def _on_titles_resolved(self, mapping):
        changed = False

        for entry in self._items:
            if not entry["title"] and entry["url"] in mapping:
                entry["title"] = mapping[entry["url"]]
                changed = True

        if not changed:
            return

        try:
            self.playback.write_playlist(self._items, self.active_playlist)

        except Exception:
            pass

        for index, entry in enumerate(self._items):
            item = self.playlist.item(index)

            if item is not None:
                item.setText(self._display_name(entry))

    def _on_titles_done(self):
        self._title_worker = None
        # A different playlist may have been selected while resolving.
        missing = [entry["url"] for entry in self._items if not entry["title"]]
        self._resolve_missing(missing)

    def remove_selected(self):
        if self.playback is None:
            return

        rows = sorted(
            (self.playlist.row(item) for item in self.playlist.selectedItems()),
            reverse=True,
        )

        if not rows:
            _set_status(self.now_label, "Select a track to remove.", "error")
            return

        for row in rows:
            if 0 <= row < len(self._items):
                url = self._items[row]["url"]

                try:
                    self.playback.remove_item(url, self.active_playlist)
                except Exception:
                    pass

        self.refresh_playlist(force=True)
        _set_status(self.now_label, f"Removed {len(rows)} track(s).", "ok")

    def load_and_play(self):
        if self.playback is None:
            return

        self.refresh_playlist(force=True)

        try:
            count = self.playback.play_playlist(self.active_playlist)

        except Exception as exc:
            _set_status(self.now_label, f"Playback error: {exc}", "error")
            return

        if count == 0:
            _set_status(self.now_label, "Playlist is empty. Add some songs first.", "error")
            return

        _set_status(self.now_label, f"Playing {count} track(s).", "ok")
        self.refresh()

    # ------------------------------------------------------------------ #
    # Transport controls
    # ------------------------------------------------------------------ #

    def _toggle(self):
        if self.playback is None:
            return

        player = self.playback.player

        try:
            has_file = bool(player.path)
        except Exception:
            has_file = False

        # Nothing loaded yet (or playback was stopped): load & play instead
        # of just flipping the pause flag on an empty player.
        if not has_file:
            self.load_and_play()
            return

        try:
            self.playback.toggle_pause()

        except Exception as exc:
            _set_status(self.now_label, f"Playback error: {exc}", "error")

        self.refresh()

    def _play_index(self, item):
        if self.playback is None:
            return

        index = self.playlist.row(item)

        try:
            self.playback.player.playlist_pos = index
            self.playback.player.pause = False
        except Exception as exc:
            _set_status(self.now_label, f"Playback error: {exc}", "error")
            return

        _set_status(self.now_label, "Loading track...", "busy")
        self.refresh()

    def _next(self):
        if self.playback is None:
            return
        self.playback.next_track()
        self.refresh()

    def _prev(self):
        if self.playback is None:
            return
        self.playback.prev_track()
        self.refresh()

    def _stop(self):
        if self.playback is None:
            return
        self.playback.stop_playback()
        self.refresh()

    def _set_volume(self, value):
        if self.playback is None:
            return

        try:
            self.playback.player.volume = value

        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Polling MPV state
    # ------------------------------------------------------------------ #

    def refresh(self):
        if self.playback is None:
            return

        player = self.playback.player

        try:
            title = player.media_title
            paused = bool(player.pause)
            position = player.time_pos
            duration = player.duration
            playlist_pos = player.playlist_pos
            idle = bool(player.core_idle)
            has_file = bool(player.path)
        except Exception:
            return

        buffering = has_file and idle and not paused and not duration

        if buffering:
            self.now_label.setText("Buffering...")
        elif title:
            self.now_label.setText(title)
        elif has_file:
            self.now_label.setText("Loading...")
        else:
            self.now_label.setText("Nothing playing")

        if playlist_pos is not None and playlist_pos >= 0:
            track = f"Track {playlist_pos + 1}"
            if self._playlist_len > 0:
                track += f" of {self._playlist_len}"
            self.track_label.setText(track + ("  -  buffering..." if buffering else ""))
            self.playlist.setCurrentRow(playlist_pos)
        else:
            self.track_label.setText("")

        self.elapsed.setText(_fmt_time(position))
        self.duration.setText(_fmt_time(duration))

        if duration and position is not None and duration > 0:
            self.progress.setValue(int(position / duration * 1000))
        else:
            self.progress.setValue(0)

        self.play_btn.setText("\u23f8" if (paused and duration) else "\u25b6")

    def stop_timer(self):
        self.timer.stop()

        if self._title_worker is not None and self._title_worker.isRunning():
            self._title_worker.stop()
            self._title_worker.wait(3000)


class SettingsPage(QWidget):
    """Local settings, currently the Discord Application ID."""

    def __init__(self, playback_module, parent=None):
        super().__init__(parent)

        self.playback = playback_module
        self.active_playlist = None

        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(14)

        title = QLabel("Settings")
        title.setObjectName("PageTitle")

        subtitle = QLabel("Connect EchoYT to your own Discord profile.")
        subtitle.setObjectName("PageSubtitle")

        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(6)

        info = QLabel(settings.DEFAULT_DISCORD_INSTRUCTIONS)
        info.setObjectName("SettingsInfo")
        info.setWordWrap(True)

        field_label = QLabel("DISCORD APPLICATION ID")
        field_label.setObjectName("SectionLabel")

        self.id_edit = QLineEdit()
        self.id_edit.setPlaceholderText("e.g. 1234567890123456789")

        self.save_btn = QPushButton("Save & Connect")
        self.save_btn.setObjectName("Primary")
        self.save_btn.clicked.connect(self.save)

        self.status = QLabel("")
        self.status.setObjectName("Status")
        self.status.setWordWrap(True)

        root.addWidget(info)
        root.addSpacing(4)
        root.addWidget(field_label)
        root.addWidget(self.id_edit)
        root.addWidget(self.save_btn)
        root.addWidget(self.status)
        root.addStretch(1)

        self.load_current()

    def load_current(self):
        current = settings.read_discord_app_id()
        self.id_edit.setText(current)

        if current:
            _set_status(self.status, "Discord App ID is saved.", "ok")
        else:
            _set_status(
                self.status,
                "No Discord App ID yet. Add one to enable Rich Presence.",
                "busy",
            )

    def save(self):
        app_id = self.id_edit.text().strip()

        if not app_id:
            _set_status(self.status, "Enter your Discord Application ID.", "error")
            return

        if not app_id.isdigit():
            _set_status(self.status, "The App ID should be numbers only.", "error")
            return

        if self.playback is None:
            settings.save_discord_app_id(app_id)
            _set_status(self.status, "Saved. Restart to connect.", "ok")
            return

        if self.playback.set_discord_app_id(app_id):
            _set_status(self.status, "Saved and connected to Discord.", "ok")
        else:
            _set_status(
                self.status,
                "Saved, but Discord is not running. Open Discord and try again.",
                "error",
            )


class MainWindow(QMainWindow):
    """Top-level window with sidebar navigation."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("EchoYT")
        self.resize(1040, 680)
        self.setMinimumSize(820, 560)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ---- sidebar ----------------------------------------------------
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(230)

        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(0)

        app_title = QLabel("EchoYT")
        app_title.setObjectName("AppTitle")

        app_subtitle = QLabel("YouTube playlist player")
        app_subtitle.setObjectName("AppSubtitle")

        self.nav = QListWidget()
        self.nav.setObjectName("SidebarList")
        self.nav.addItems(["  Add Songs", "  Player", "  Settings"])
        self.nav.setCurrentRow(0)
        self.nav.setFixedHeight(140)

        # ---- playlist manager ------------------------------------------
        pl_label = QLabel("PLAYLISTS")
        pl_label.setObjectName("SidebarSection")

        self.playlist_combo = QComboBox()
        self.playlist_combo.setObjectName("PlaylistCombo")
        self.playlist_combo.currentTextChanged.connect(self._on_playlist_selected)

        new_btn = QPushButton("New")
        new_btn.setObjectName("SidebarButton")
        new_btn.clicked.connect(self.create_playlist)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("SidebarButton")
        delete_btn.clicked.connect(self.delete_playlist)

        pl_buttons = QHBoxLayout()
        pl_buttons.setContentsMargins(0, 0, 0, 0)
        pl_buttons.setSpacing(8)
        pl_buttons.addWidget(new_btn, 1)
        pl_buttons.addWidget(delete_btn, 1)

        pl_box = QWidget()
        pl_box.setObjectName("SidebarPlaylists")
        pl_box_layout = QVBoxLayout(pl_box)
        pl_box_layout.setContentsMargins(16, 4, 16, 12)
        pl_box_layout.setSpacing(8)
        pl_box_layout.addWidget(pl_label)
        pl_box_layout.addWidget(self.playlist_combo)
        pl_box_layout.addLayout(pl_buttons)

        footer = QLabel("Powered by mpv & yt-dlp")
        footer.setObjectName("SidebarFooter")
        footer.setWordWrap(True)

        side_layout.addWidget(app_title)
        side_layout.addWidget(app_subtitle)
        side_layout.addWidget(self.nav)
        side_layout.addWidget(pl_box)
        side_layout.addStretch(1)
        side_layout.addWidget(footer)

        # ---- pages ------------------------------------------------------
        self.pages = QStackedWidget()

        self.add_page = AddSongPage()
        self.player_page = PlayerPage(PLAYBACK)
        self.settings_page = SettingsPage(PLAYBACK)

        self.pages.addWidget(self.add_page)
        self.pages.addWidget(self.player_page)
        self.pages.addWidget(self.settings_page)

        self.nav.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.add_page.playlistChanged.connect(
            lambda: self.player_page.refresh_playlist(force=True)
        )

        layout.addWidget(sidebar)
        layout.addWidget(self.pages, 1)

        self.setCentralWidget(central)

        self.current_playlist = None
        self._reload_playlists()

        self.statusBar().showMessage("Ready")

        if PLAYBACK is None:
            self.statusBar().showMessage("Playback engine unavailable")

        # First-run setup: ask for the Discord App ID if none is saved yet.
        if not settings.read_discord_app_id():
            QTimer.singleShot(300, self.prompt_discord_setup)

    def prompt_discord_setup(self):
        app_id, ok = QInputDialog.getText(
            self,
            "Discord setup (optional)",
            settings.DEFAULT_DISCORD_INSTRUCTIONS + "\nApplication ID:",
        )

        if not ok or not app_id.strip():
            self.statusBar().showMessage("Discord setup skipped - you can add it in Settings.")
            return

        app_id = app_id.strip()

        if PLAYBACK is not None:
            connected = PLAYBACK.set_discord_app_id(app_id)
        else:
            settings.save_discord_app_id(app_id)
            connected = False

        self.settings_page.id_edit.setText(app_id)

        if connected:
            _set_status(self.settings_page.status, "Saved and connected to Discord.", "ok")
            self.statusBar().showMessage("Discord connected")
        else:
            _set_status(
                self.settings_page.status,
                "Saved. Open Discord and press 'Save & Connect' to retry.",
                "busy",
            )
            self.statusBar().showMessage("Discord App ID saved")

    # ------------------------------------------------------------------ #
    # Playlist management
    # ------------------------------------------------------------------ #

    def _reload_playlists(self, select=None):
        names = playlists.list_playlists()

        self.playlist_combo.blockSignals(True)
        self.playlist_combo.clear()
        self.playlist_combo.addItems(names)

        if select and select in names:
            self.playlist_combo.setCurrentText(select)

        self.playlist_combo.blockSignals(False)

        self._on_playlist_selected(self.playlist_combo.currentText())

    def _on_playlist_selected(self, name):
        if not name:
            return

        self.current_playlist = name
        self.add_page.set_active_playlist(name)
        self.player_page.set_active_playlist(name)
        self.statusBar().showMessage(f"Playlist: {name}")

    def create_playlist(self):
        name, ok = QInputDialog.getText(self, "New Playlist", "Playlist name:")

        if not ok or not name.strip():
            return

        try:
            created = playlists.create_playlist(name)

        except Exception as exc:
            QMessageBox.warning(self, "Could not create playlist", str(exc))
            return

        self._reload_playlists(select=created)
        self.statusBar().showMessage(f"Created playlist '{created}'")

    def delete_playlist(self):
        name = self.playlist_combo.currentText()

        if not name:
            return

        if len(playlists.list_playlists()) <= 1:
            QMessageBox.information(
                self, "Cannot delete", "At least one playlist must remain."
            )
            return

        reply = QMessageBox.question(
            self,
            "Delete Playlist",
            f"Delete playlist '{name}' and all of its tracks?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        try:
            playlists.remove_playlist(name)

        except Exception as exc:
            QMessageBox.warning(self, "Could not delete playlist", str(exc))
            return

        self._reload_playlists()
        self.statusBar().showMessage(f"Deleted playlist '{name}'")

    def closeEvent(self, event):
        self.add_page.stop_search()
        self.player_page.stop_timer()

        if self.playback_available():
            try:
                PLAYBACK.shutdown()

            except Exception:
                pass

        super().closeEvent(event)

    @staticmethod
    def playback_available():
        return PLAYBACK is not None
