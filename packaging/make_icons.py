"""Regenerate every app icon from packaging/icon.svg (macOS only: needs rsvg-convert and iconutil).

    brew install librsvg
    python3 packaging/make_icons.py

Writes:
  packaging/icon.icns                     the macOS app
  packaging/icon.ico                      the Windows exe and shortcuts (16-256 px)
  password_manager/assets/app-icon.png    512 px: the Linux menu entry and the window icon
  password_manager/assets/icon/app-N.png  16-256 px, so window and taskbar icons are sharp at every size
  password_manager/assets/icon/{back,shackle,front}.png
                                          the same icon in three layers, so the app can lift the shackle
                                          while it unlocks; stacked, they are exactly app-icon.png
"""

import re
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
ASSETS = HERE.parent / "password_manager" / "assets"
PNG = ASSETS / "app-icon.png"
SIZES = ASSETS / "icon"
WINDOW_SIZES = (16, 24, 32, 48, 64, 128, 256)
LAYERS = {"back": ("back-shadow", "back"), "shackle": ("shackle",), "front": ("front", "front-rim")}
LAYER_SIZE = 512


def render(size: int, out: Path, svg: Path = SVG) -> None:
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), str(svg), "-o", str(out)], check=True)


def layer_svg(keep, tmp: Path) -> Path:
    """icon.svg with every named layer hidden except `keep`."""
    text = SVG.read_text(encoding="utf-8")
    names = [name for group in LAYERS.values() for name in group]
    for name in names:
        if name not in keep:
            text, count = re.subn(rf'<g id="{name}"', f'<g id="{name}" display="none"', text)
            if count != 1:
                raise SystemExit(f'icon.svg needs exactly one <g id="{name}"> layer')
    out = tmp / f"layer-{'-'.join(keep)}.svg"
    out.write_text(text, encoding="utf-8")
    return out


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
    SIZES.mkdir(parents=True, exist_ok=True)
    written = [ICNS, ICO, PNG]
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        iconset = tmp / "icon.iconset"
        iconset.mkdir()
        for size in (16, 32, 128, 256, 512):
            render(size, iconset / f"icon_{size}x{size}.png")
            render(size * 2, iconset / f"icon_{size}x{size}@2x.png")
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(ICNS)], check=True)

        pngs = {}
        for size in WINDOW_SIZES:
            pngs[size] = SIZES / f"app-{size}.png"
            render(size, pngs[size])
            written.append(pngs[size])
        write_ico({size: pngs[size] for size in (16, 24, 32, 48, 64, 128, 256)})

        for name, keep in LAYERS.items():
            out = SIZES / f"{name}.png"
            render(LAYER_SIZE, out, layer_svg(keep, tmp))
            written.append(out)

    render(LAYER_SIZE, PNG)
    for path in written:
        print(f"wrote {path.relative_to(HERE.parent)} ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
