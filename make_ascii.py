#!/usr/bin/env python3
"""Turn a portrait photo into ASCII art and save it as art.txt.

Usage: python3 make_ascii.py PHOTO [--crop L,T,R,B] [--cols N] [--rows N]
       [--black N] [--white N] [--gamma G]

Run once locally. Only art.txt (plain text) is meant to be committed; keep the
original photo out of the repo. Brighter pixels map to denser characters, so a
dark background stays empty.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

RAMP = " .:-=+*#%@"  # short ramp keeps the card readable at small sizes


def build(photo: Path, crop: tuple[int, int, int, int] | None, cols: int, rows: int,
          black: int, white: int, gamma: float) -> list[str]:
    img = Image.open(photo)
    img = ImageOps.exif_transpose(img).convert("L")
    if crop:
        img = img.crop(crop)
    img = img.filter(ImageFilter.GaussianBlur(radius=3))
    # Boost local detail so facial features survive the tiny resolution.
    img = img.filter(ImageFilter.UnsharpMask(radius=25, percent=250, threshold=0))
    img = img.resize((cols, rows), Image.LANCZOS)
    px = img.load()
    lines = []
    for y in range(rows):
        chars = []
        for x in range(cols):
            v = min(max((px[x, y] - black) / (white - black), 0.0), 1.0) ** gamma
            chars.append(RAMP[min(int(v * len(RAMP)), len(RAMP) - 1)])
        lines.append("".join(chars).rstrip())
    return lines


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("photo", type=Path)
    ap.add_argument("--crop", default="470,70,1090,930", help="L,T,R,B in source pixels")
    ap.add_argument("--cols", type=int, default=69)
    ap.add_argument("--rows", type=int, default=50)
    ap.add_argument("--black", type=int, default=60, help="levels: below this is empty (hides background)")
    ap.add_argument("--white", type=int, default=225, help="levels: above this is the densest character")
    ap.add_argument("--gamma", type=float, default=1.2)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent / "art.txt")
    a = ap.parse_args()
    crop = tuple(int(v) for v in a.crop.split(",")) if a.crop else None
    lines = build(a.photo, crop, a.cols, a.rows, a.black, a.white, a.gamma)
    a.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {a.out} ({a.cols}x{a.rows})")


if __name__ == "__main__":
    main()
