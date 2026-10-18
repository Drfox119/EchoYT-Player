# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller build spec for EchoYT.

Build with:

    pyinstaller --noconfirm --clean echoyt.spec

Output:
    dist/EchoYT/EchoYT(.exe)  plus a ``_internal`` folder (onedir).

On Windows, place ``libmpv-2.dll`` next to this spec (the release workflow
downloads it automatically) so it gets bundled and found at runtime.
"""

import os
import sys

from PyInstaller.utils.hooks import collect_submodules

project_root = os.path.abspath(os.getcwd())

binaries = []

# Bundle libmpv on Windows when it has been provided next to the project.
if sys.platform.startswith("win"):
    for _name in ("libmpv-2.dll", "mpv-2.dll", "mpv-1.dll"):
        _path = os.path.join(project_root, _name)

        if os.path.isfile(_path):
            binaries.append((_path, "."))
            break

    # libmpv hard-links the Vulkan loader, so ship it too (see
    # packaging/get_libmpv.py); without it the engine fails to load on
    # systems that have no GPU Vulkan driver.
    _vulkan = os.path.join(project_root, "vulkan-1.dll")

    if os.path.isfile(_vulkan):
        binaries.append((_vulkan, "."))

hiddenimports = [
    "mpv",
    "pypresence",
    "jeepney",
    "jeepney.io.blocking",
    "jeepney.bus_messages",
] + collect_submodules("jeepney")

a = Analysis(
    ["echoyt.py"],
    pathex=[project_root],
    binaries=binaries,
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EchoYT",
    debug=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="EchoYT",
)
