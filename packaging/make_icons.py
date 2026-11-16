"""Regenerate the app icons from packaging/icon.svg (macOS only: needs rsvg-convert and iconutil).

    brew install librsvg
    python3 packaging/make_icons.py

Writes packaging/icon.icns (macOS app), packaging/icon.ico (Windows exe and shortcuts) and
password_manager/assets/app-icon.png (Tk window icon; also used by the Linux menu entry).
"""

import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SVG = HERE / "icon.svg"
ICNS = HERE / "icon.icns"
ICO = HERE / "icon.ico"
PNG = HERE.parent / "password_manager" / "assets" / "app-icon.png"


def render(size: int, out: Path) -> None:
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), str(SVG), "-o", str(out)], check=True)


def write_ico(pngs: dict) -> None:
    """An .ico whose entries are PNG images (supported since Windows Vista)."""
    sizes = sorted(pngs)
    blobs = [pngs[s].read_bytes() for s in sizes]
    offset = 6 + 16 * len(sizes)
    header = struct.pack("<HHH", 0, 1, len(sizes))
    entries = b""
    for size, blob in zip(sizes, blobs):
        dim = 0 if size >= 256 else size  # 0 means 256 in the ICO directory
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    ICO.write_bytes(header + entries + b"".join(blobs))


def main() -> int:
    for tool in ("rsvg-convert", "iconutil"):
        if not shutil.which(tool):
            print(f"{tool} not found (rsvg-convert: brew install librsvg; iconutil ships with macOS)")
            return 1
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "icon.iconset"
        iconset.mkdir()
        for size in (16, 32, 128, 256, 512):
            render(size, iconset / f"icon_{size}x{size}.png")
            render(size * 2, iconset / f"icon_{size}x{size}@2x.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(ICNS)], check=True)

        pngs = {}
        for size in (16, 24, 32, 48, 64, 128, 256):
            pngs[size] = Path(tmp) / f"ico_{size}.png"
            render(size, pngs[size])
        write_ico(pngs)

    render(256, PNG)
    for path in (ICNS, ICO, PNG):
        print(f"wrote {path.relative_to(HERE.parent)} ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
