#!/usr/bin/env python3
"""Build larger sidebar marks; reserve whitespace after each logo in the UI."""
from fontTools.ttLib import TTFont

try:
    from .build_font import ROOT, svg_glyph, FONT_TIMESTAMP
except ImportError:
    from build_font import ROOT, svg_glyph, FONT_TIMESTAMP


def build(output=None):
    font = TTFont(ROOT / "dist/HerdrHarnessLogos-Regular.ttf")
    for name in ("claude", "codex"):
        source = ROOT / (
            "assets/svg/claude.svg" if name == "claude" else "font/sidebar/codex.svg"
        )
        glyph = svg_glyph(source, max_width=760, max_height=760, center_y=365)
        glyph.recalcBounds(font["glyf"])
        font["glyf"][name] = glyph
        font["hmtx"].metrics[name] = (600, glyph.xMin)
    names = {
        1: "Herdr Sidebar Logos", 2: "Regular", 3: "herdr-sidebar-logos:1.0.0",
        4: "Herdr Sidebar Logos Regular", 5: "Version 1.0.0",
        6: "HerdrSidebarLogos-Regular",
    }
    for record in font["name"].names:
        if record.nameID in names:
            record.string = names[record.nameID].encode(record.getEncoding())
    font["hhea"].ascent = 1020
    font["OS/2"].sTypoAscender = font["OS/2"].usWinAscent = 1020
    font["hhea"].descent = font["OS/2"].sTypoDescender = -300
    font["OS/2"].usWinDescent = 300
    font["head"].modified = FONT_TIMESTAMP
    font.recalcTimestamp = False
    output = output or ROOT / "dist/HerdrSidebarLogos-Regular.ttf"
    font.save(output)
    print(output)


if __name__ == "__main__":
    build()
