#!/usr/bin/env python3
"""Package Stribe into a single shareable zip.

    python build_bundle.py

Produces dist/Stribe-<version>-windows.zip containing everything a recipient
needs: the app, its assets and fonts, the bundled ffmpeg, and a
double-clickable installer.

Development-only files (the design concepts, the asset build scripts, the
sample recording, git metadata) are deliberately left out.
"""
from __future__ import annotations

import re
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"

# Everything the installed app actually needs at runtime.
FILES = [
    "app.py",
    "theme.py",
    "widgets.py",
    "transcribe.py",
    "requirements.txt",
    "install.ps1",
    "uninstall.ps1",
    "Install Stribe.bat",
    "Uninstall Stribe.bat",
    "Stribe.bat",
    "ffmpeg.exe",
]

ASSET_PATTERNS = [
    "assets/logo.png",
    "assets/icon.png",
    "assets/hero.png",
    "assets/stribe.ico",
    "assets/fonts/*.ttf",
    "assets/fonts/OFL-*.txt",
]

# The bundle ships the recipient-facing readme under the standard name.
README_SOURCE = "README-bundle.md"
README_TARGET = "README.md"


def version() -> str:
    text = (ROOT / "app.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*"([^"]+)"', text, re.M)
    if not match:
        raise SystemExit("VERSION not found in app.py")
    return match.group(1)


def collect() -> list[tuple[Path, str]]:
    """Pairs of (source path, path inside the zip)."""
    items: list[tuple[Path, str]] = []

    for name in FILES:
        path = ROOT / name
        if not path.exists():
            raise SystemExit(f"missing required file: {name}")
        items.append((path, name))

    for pattern in ASSET_PATTERNS:
        matches = sorted(ROOT.glob(pattern))
        if not matches:
            raise SystemExit(f"no files matched: {pattern}")
        for path in matches:
            items.append((path, path.relative_to(ROOT).as_posix()))

    readme = ROOT / README_SOURCE
    if not readme.exists():
        raise SystemExit(f"missing {README_SOURCE}")
    items.append((readme, README_TARGET))

    # Exclude the variable font sources - only the static cuts are loaded.
    return [(src, dst) for src, dst in items if not src.stem.endswith("-VF")]


def main() -> None:
    ver = version()
    DIST.mkdir(exist_ok=True)
    archive = DIST / f"Stribe-{ver}-windows.zip"
    if archive.exists():
        archive.unlink()

    items = collect()
    root_folder = "Stribe"

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for src, dst in items:
            zf.write(src, f"{root_folder}/{dst}")

    total = sum(src.stat().st_size for src, _ in items)
    print(f"{archive.relative_to(ROOT)}")
    print(f"  {len(items)} files, {total / 1e6:.1f} MB raw -> "
          f"{archive.stat().st_size / 1e6:.1f} MB zipped")
    print(f"\nShare that zip. The recipient extracts it and runs "
          f"\"Install Stribe.bat\".")


if __name__ == "__main__":
    main()
