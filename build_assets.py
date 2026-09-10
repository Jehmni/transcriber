#!/usr/bin/env python3
"""Turn the raw generated art into the assets the app ships with.

Run this only when the source art changes:

    python build_assets.py

Inputs   : assets/logo_raw.png, assets/hero_raw.png
Outputs  : assets/logo.png, assets/hero.png, assets/stribe.ico
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

ASSETS = Path(__file__).resolve().parent / "assets"

# Stargit tokens used by the icon tile.
TILE_TOP = (30, 41, 59)      # #1E293B  Layer 2
TILE_BOTTOM = (2, 6, 23)     # #020617  Layer 0


def key_out_background(src: Image.Image, lo: int = 16, hi: int = 96) -> Image.Image:
    """Give the glowing mark an alpha channel derived from its own luminance.

    The art sits on a flat near-black navy field, so luminance is a faithful
    stand-in for coverage and it keeps the soft outer glow intact.
    """
    rgb = src.convert("RGB")
    lum = rgb.convert("L")
    alpha = lum.point(lambda v: 0 if v <= lo else min(255, int((v - lo) * 255 / (hi - lo))))
    out = rgb.copy()
    out.putalpha(alpha)
    return out


def trim(img: Image.Image, pad_ratio: float = 0.04) -> Image.Image:
    """Crop to the visible mark, then re-pad evenly and square it up."""
    bbox = img.split()[-1].getbbox()
    if bbox:
        img = img.crop(bbox)
    side = max(img.size)
    pad = int(side * pad_ratio)
    canvas = Image.new("RGBA", (side + 2 * pad, side + 2 * pad), (0, 0, 0, 0))
    canvas.paste(img, ((canvas.width - img.width) // 2, (canvas.height - img.height) // 2), img)
    return canvas


def build_logo() -> Image.Image:
    raw = Image.open(ASSETS / "logo_raw.png")
    mark = trim(key_out_background(raw))
    mark = mark.resize((512, 512), Image.LANCZOS)
    mark.save(ASSETS / "logo.png")
    print(f"assets/logo.png        {mark.size}  transparent mark")
    return mark


def rounded_mask(size: int, radius_ratio: float = 0.22) -> Image.Image:
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size * 4 - 1, size * 4 - 1),
        radius=int(size * 4 * radius_ratio),
        fill=255,
    )
    return mask.resize((size, size), Image.LANCZOS)


def build_icon(mark: Image.Image) -> None:
    """A rounded navy tile behind the mark - far more legible at 16-32px."""
    base = 512
    tile = Image.new("RGBA", (base, base))
    draw = ImageDraw.Draw(tile)
    for y in range(base):                       # vertical Layer2 -> Layer0 gradient
        t = y / (base - 1)
        draw.line(
            [(0, y), (base, y)],
            fill=tuple(int(a + (b - a) * t) for a, b in zip(TILE_TOP, TILE_BOTTOM)) + (255,),
        )
    tile.putalpha(rounded_mask(base))

    inner = mark.resize((int(base * 0.82),) * 2, Image.LANCZOS)
    glow = inner.filter(ImageFilter.GaussianBlur(base * 0.03))
    pos = ((base - inner.width) // 2, (base - inner.height) // 2)
    tile.alpha_composite(glow, pos)
    tile.alpha_composite(inner, pos)

    sizes = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256)]
    tile.save(ASSETS / "stribe.ico", format="ICO", sizes=sizes)
    tile.resize((256, 256), Image.LANCZOS).save(ASSETS / "icon.png")
    print(f"assets/stribe.ico      {[s[0] for s in sizes]}")
    print("assets/icon.png        256x256")


def build_hero() -> None:
    """Tone the backdrop down and fade its edges into the page background.

    Without the fade the artwork ends on a hard vertical seam wherever the
    header happens to be cropped.
    """
    hero = Image.open(ASSETS / "hero_raw.png").convert("RGB")
    w, h = hero.size
    base = Image.new("RGB", (w, h), TILE_BOTTOM)
    hero = Image.blend(hero, base, 0.35)

    def ramp(value: float) -> float:
        """Clamp to 0..1 - int() flooring can push the first step negative,
        and a negative base with a fractional exponent is a complex number."""
        return min(1.0, max(0.0, value))

    fade = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(fade)
    for x in range(int(w * 0.5), w):                 # right edge -> background
        t = ramp((x - w * 0.5) / (w * 0.5))
        draw.line([(x, 0), (x, h)], fill=int(255 * (1 - t ** 1.4)))
    bottom = Image.new("L", (w, h), 255)
    bdraw = ImageDraw.Draw(bottom)
    for y in range(int(h * 0.55), h):                # bottom edge -> background
        t = ramp((y - h * 0.55) / (h * 0.45))
        bdraw.line([(0, y), (w, y)], fill=int(255 * (1 - t ** 1.6)))
    fade = ImageChops.multiply(fade, bottom)

    hero = Image.composite(hero, base, fade)
    hero.save(ASSETS / "hero.png")
    print(f"assets/hero.png        {hero.size}  toned, edges faded to background")


if __name__ == "__main__":
    build_hero()
    build_icon(build_logo())
    print("\nassets rebuilt.")
