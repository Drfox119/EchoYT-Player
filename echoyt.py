"""Entry point for frozen (PyInstaller) builds and simple launching.

Running ``python echoyt.py`` starts the GUI, exactly like ``python -m gui``.
"""

import sys

from gui.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
