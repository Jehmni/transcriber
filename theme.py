"""Stribe design tokens - Stargit Solutions brand system.

Colour, type and spacing values come from the Stargit design system:
a four-tier dark surface stack, an electric-blue -> indigo -> cyan accent
gradient, Space Grotesk for display and Inter for body copy.
"""
from __future__ import annotations

import ctypes
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
FONT_DIR = ASSETS / "fonts"

# --------------------------------------------------------------------- colour
# Surface stack (Layer 0 -> Layer 3)
BG = "#020617"          # Layer 0  pure background
SURFACE_1 = "#0F172A"   # Layer 1  section containers
SURFACE_2 = "#1E293B"   # Layer 2  cards / panels
SURFACE_3 = "#334155"   # Layer 3  hover / active

# Accent gradient
PRIMARY = "#3B82F6"     # electric blue
PRIMARY_GLOW = "#60A5FA"
INDIGO = "#6366F1"
CYAN = "#06B6D4"

# Text hierarchy
TEXT_HEADING = "#FFFFFF"
TEXT_BODY = "#B8C2D1"
TEXT_MUTED = "#7E8CA6"

# Lines and states
BORDER = "#1E2A42"
BORDER_STRONG = "#2C3B58"
SUCCESS = "#34D399"
DANGER = "#F87171"

ACCENT_GRADIENT = (PRIMARY, INDIGO, CYAN)

# ---------------------------------------------------------------- proportions
RADIUS_SM = 8
RADIUS = 12
RADIUS_LG = 16

SPACE = 8               # base spacing unit; multiples used throughout

# Motion - "intelligent, precise, engineering-inspired"
MOTION_MS = 280
FRAME_MS = 16


# --------------------------------------------------------------------- fonts
DISPLAY = "Space Grotesk Bold"
DISPLAY_MEDIUM = "Space Grotesk Medium"
BODY = "Inter"
BODY_MEDIUM = "Inter Medium"
BODY_SEMIBOLD = "Inter SemiBold"

_FALLBACKS = {
    DISPLAY: "Segoe UI Semibold",
    DISPLAY_MEDIUM: "Segoe UI Semibold",
    BODY: "Segoe UI",
    BODY_MEDIUM: "Segoe UI",
    BODY_SEMIBOLD: "Segoe UI Semibold",
}

_FR_PRIVATE = 0x10


def load_fonts() -> None:
    """Register the bundled brand fonts for this process only.

    No installation, no admin rights - the fonts simply exist for as long as
    the app runs. Must be called before the first Tk font lookup.
    """
    if sys.platform != "win32" or not FONT_DIR.is_dir():
        return
    for ttf in sorted(FONT_DIR.glob("*.ttf")):
        if ttf.stem.endswith("-VF"):
            continue                                  # variable source files
        try:
            ctypes.windll.gdi32.AddFontResourceExW(str(ttf), _FR_PRIVATE, 0)
        except Exception:                             # noqa: BLE001
            pass


def resolve_fonts(available: set[str]) -> None:
    """Swap in system fallbacks for any brand font Tk cannot see."""
    global DISPLAY, DISPLAY_MEDIUM, BODY, BODY_MEDIUM, BODY_SEMIBOLD
    resolved = {}
    for name in (DISPLAY, DISPLAY_MEDIUM, BODY, BODY_MEDIUM, BODY_SEMIBOLD):
        resolved[name] = name if name in available else _FALLBACKS[name]
    DISPLAY = resolved[DISPLAY]
    DISPLAY_MEDIUM = resolved[DISPLAY_MEDIUM]
    BODY = resolved[BODY]
    BODY_MEDIUM = resolved[BODY_MEDIUM]
    BODY_SEMIBOLD = resolved[BODY_SEMIBOLD]


# --------------------------------------------------------------------- scale
# Set once at startup from the display DPI. Widgets take logical pixels and
# convert through px() so the layout holds up on scaled displays.
SCALE = 1.0


def set_scale(factor: float) -> None:
    global SCALE
    SCALE = factor


def px(value: float) -> int:
    return int(round(value * SCALE))


# ------------------------------------------------------------------- helpers
def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def mix(a: str, b: str, t: float) -> str:
    """Blend two hex colours; t=0 returns a, t=1 returns b."""
    ra, ga, ba = hex_to_rgb(a)
    rb, gb, bb = hex_to_rgb(b)
    return "#%02x%02x%02x" % (
        round(ra + (rb - ra) * t),
        round(ga + (gb - ga) * t),
        round(ba + (bb - ba) * t),
    )


def ease_out(t: float) -> float:
    """Cubic ease-out - no bounce, per the brand motion philosophy."""
    return 1 - pow(1 - t, 3)
