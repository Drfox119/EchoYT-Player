"""Entry point: run with ``python -m gui`` from the project directory."""

import sys
from pathlib import Path

# Make sure the project root (with config.py, newsongs.py, playback.py)
# is importable regardless of where the command is launched from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication  # noqa: E402

from gui.main_window import MainWindow  # noqa: E402
from gui.theme import apply_theme  # noqa: E402


def main():
    app = QApplication(sys.argv)
    apply_theme(app)

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
