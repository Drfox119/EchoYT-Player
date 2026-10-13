"""Background threads so long-running work never blocks the UI."""

from PySide6.QtCore import QThread, Signal

import newsongs


class SearchWorker(QThread):
    """Runs a YouTube search on a worker thread.

    Signals:
        succeeded(list): emitted with the list of {"title", "url"} results.
        failed(str):     emitted with a human readable error message.
    """

    succeeded = Signal(list)
    failed = Signal(str)

    def __init__(self, query: str, max_results: int, parent=None):
        super().__init__(parent)
        self.query = query
        self.max_results = max_results
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            results = newsongs.search_videos(self.query, self.max_results)

        except Exception as exc:  # network / yt-dlp failures
            if not self._stop:
                self.failed.emit(f"Search failed: {exc}")
            return

        if self._stop:
            return

        if not results:
            self.failed.emit("No results found for that query.")
            return

        self.succeeded.emit(results)


class TitleWorker(QThread):
    """Resolves titles for playlist URLs that do not have one yet.

    Signals:
        resolved(dict): emitted with a {url: title} mapping.
    """

    resolved = Signal(dict)

    def __init__(self, urls, parent=None):
        super().__init__(parent)
        self.urls = list(urls)
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        titles = {}

        for url in self.urls:
            if self._stop:
                break

            try:
                title = newsongs.fetch_title(url)

            except Exception:
                continue

            if title:
                titles[url] = title

        if titles and not self._stop:
            self.resolved.emit(titles)
