"""Download the Windows runtime bits needed to bundle EchoYT.

Two things live next to this build on Windows:

* ``libmpv-2.dll`` - the playback engine, from shinchiro's
  mpv-winbuild-cmake releases.
* ``vulkan-1.dll`` - the Khronos Vulkan loader. mpv hard-links against it
  (it is a normal load-time import), so the engine cannot load on machines
  that lack a GPU Vulkan driver, such as many VMs and RDP sessions. We ship
  the redistributable LunarG runtime loader so playback always starts; mpv
  only ever *touches* Vulkan for video output, and EchoYT is audio-only.

Usage:  python packaging/get_libmpv.py [dest_dir]

An ``7z``/``7za``/``7zr`` executable is required to unpack the mpv ``.7z``
(the archive uses the BCJ2 filter, which pure-python extractors cannot
handle). On Windows the 7-Zip bundled with the GitHub runners is picked up
automatically.
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

API = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"
HEADERS = {"User-Agent": "echoyt-build"}

VULKAN_LATEST = "https://vulkan.lunarg.com/sdk/latest/windows.txt"
VULKAN_RUNTIME = (
    "https://sdk.lunarg.com/sdk/download/latest/windows/"
    "VulkanRT-X64-{version}-Components.zip"
)

WINDOWS_7Z_PATHS = (
    r"C:\Program Files\7-Zip\7z.exe",
    r"C:\Program Files (x86)\7-Zip\7z.exe",
)


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS))


def _find_7z():
    for exe in ("7z", "7za", "7zr"):
        path = shutil.which(exe)

        if path:
            return path

    for path in WINDOWS_7Z_PATHS:
        if os.path.isfile(path):
            return path

    return None


def _fetch_libmpv(dest):
    with _get(API) as resp:
        release = json.load(resp)

    assets = release.get("assets", [])

    def _dev(name):
        return name.startswith("mpv-dev-x86_64-") and name.endswith(".7z")

    # Prefer the plain x86_64 build over the AVX2-only "v3" variant.
    candidates = [a for a in assets if _dev(a["name"]) and "-v3-" not in a["name"]]
    candidates += [a for a in assets if _dev(a["name"]) and "-v3-" in a["name"]]

    if not candidates:
        sys.exit("No mpv-dev-x86_64 asset found in the latest release")

    asset = candidates[0]
    print("Downloading", asset["browser_download_url"])

    with _get(asset["browser_download_url"]) as resp:
        raw = resp.read()

    sevenzip = _find_7z()

    if sevenzip is None:
        sys.exit(
            "7-Zip (7z) was not found. Install p7zip/7-Zip so the .7z archive "
            "can be unpacked."
        )

    with tempfile.TemporaryDirectory() as tmp:
        archive_path = os.path.join(tmp, "mpv.7z")

        with open(archive_path, "wb") as fh:
            fh.write(raw)

        subprocess.run(
            [sevenzip, "e", "-y", "-o" + os.path.abspath(dest), archive_path,
             "libmpv-2.dll"],
            check=True,
        )

    target = os.path.join(dest, "libmpv-2.dll")

    if not os.path.isfile(target):
        sys.exit("libmpv-2.dll was not extracted from the archive")

    print("Saved", target)


def _fetch_vulkan_loader(dest):
    with _get(VULKAN_LATEST) as resp:
        version = resp.read().decode("ascii").strip()

    url = VULKAN_RUNTIME.format(version=version)
    print("Downloading", url)

    with _get(url) as resp:
        raw = resp.read()

    target = os.path.join(dest, "vulkan-1.dll")

    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        members = [
            name for name in archive.namelist()
            if name.replace("\\", "/").lower().endswith("/x64/vulkan-1.dll")
            or name.replace("\\", "/").lower() == "vulkan-1.dll"
        ]

        if not members:
            sys.exit("vulkan-1.dll (x64) not found in the Vulkan runtime zip")

        with archive.open(members[0]) as src, open(target, "wb") as out:
            shutil.copyfileobj(src, out)

    print("Saved", target)


def main(dest="."):
    os.makedirs(dest, exist_ok=True)
    _fetch_libmpv(dest)
    _fetch_vulkan_loader(dest)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
