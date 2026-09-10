#!/usr/bin/env python3
"""Instance the variable brand fonts into the static weights the app loads.

Space Grotesk and Inter ship from Google Fonts as variable fonts, but Windows
GDI - which Tk draws through - only exposes a variable font's default instance,
so bold would come out synthesised. Cutting real static instances avoids that.

Run this only when the fonts are updated:

    python build_fonts.py

Both families are SIL Open Font License; see assets/fonts/OFL-*.txt.
"""
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"

# source, output, axis coordinates, family name exposed to Tk
JOBS = [
    ("SpaceGrotesk-VF.ttf", "SpaceGrotesk-Medium.ttf", {"wght": 500}, "Space Grotesk Medium"),
    ("SpaceGrotesk-VF.ttf", "SpaceGrotesk-Bold.ttf", {"wght": 700}, "Space Grotesk Bold"),
    ("Inter-VF.ttf", "Inter-Regular.ttf", {"wght": 400, "opsz": 14}, "Inter"),
    ("Inter-VF.ttf", "Inter-Medium.ttf", {"wght": 500, "opsz": 14}, "Inter Medium"),
    ("Inter-VF.ttf", "Inter-SemiBold.ttf", {"wght": 600, "opsz": 14}, "Inter SemiBold"),
]


def set_family(font: TTFont, family: str) -> None:
    """Give each weight its own family name.

    Tk selects fonts by family plus a weight keyword, and it cannot address
    'Medium' or 'SemiBold'. Naming every instance as its own Regular family
    lets the app ask for exactly the weight it wants.
    """
    name = font["name"]
    for record in list(name.names):
        if record.nameID in (1, 2, 4, 6, 16, 17):
            name.removeNames(record.nameID, record.platformID, record.platEncID, record.langID)
    for platform_id, encoding_id, language_id in ((3, 1, 0x409), (1, 0, 0)):
        name.setName(family, 1, platform_id, encoding_id, language_id)
        name.setName("Regular", 2, platform_id, encoding_id, language_id)
        name.setName(family, 4, platform_id, encoding_id, language_id)
        name.setName(family.replace(" ", ""), 6, platform_id, encoding_id, language_id)


def main() -> None:
    for source, output, coords, family in JOBS:
        font = TTFont(FONT_DIR / source)
        static = instancer.instantiateVariableFont(font, coords, inplace=True, updateFontNames=False)
        set_family(static, family)
        static.save(FONT_DIR / output)
        print(f"{output:28} <- {source:22} {coords}  family={family!r}")
    print("\nfonts rebuilt.")


if __name__ == "__main__":
    main()
