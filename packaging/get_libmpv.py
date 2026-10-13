"""Download a Windows ``libmpv-2.dll`` for bundling into the release build.

Grabs the latest ``mpv-dev-x86_64`` archive from shinchiro's mpv-winbuild-cmake
releases and extracts ``libmpv-2.dll`` into the given directory.

Usage:  python packaging/get_libmpv.py [dest_dir]

Only intended for the Windows CI job (requires the ``py7zr`` package).
"""

import io
import json
import os
import sys
import urllib.request

API = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"
HEADERS = {"User-Agent": "echoyt-build"}


def _get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS))


def main(dest="."):
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

    import py7zr

    with py7zr.SevenZipFile(io.BytesIO(raw)) as archive:
        members = [n for n in archive.getnames()
                   if os.path.basename(n).lower() == "libmpv-2.dll"]

        if not members:
            sys.exit("libmpv-2.dll not present in the archive")

        archive.extract(path=dest, targets=members)

    extracted = os.path.join(dest, members[0])
    target = os.path.join(dest, "libmpv-2.dll")

    if os.path.abspath(extracted) != os.path.abspath(target):
        os.replace(extracted, target)

    print("Saved", target)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
