#!/usr/bin/env python3
"""Build the deterministic one-cell Herdr harness logo font."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path
from xml.etree import ElementTree

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib.path import SVGPath

ROOT = Path(__file__).resolve().parents[1]
UPM = 1000
ADVANCE = 600
ASCENT = 800
DESCENT = -200
FONT_TIMESTAMP = 2082844800  # 1970-01-01 in OpenType's 1904 epoch.
STABLE_GLYPH_ORDER = (
    "claude",
    "codex",
    "opencode",
    "omp",
    "cline",
    "mastracode",
    "kimi",
    "kilo",
    "maki",
)


def svg_glyph(path: Path, *, max_width=460, max_height=760, center_y=300):
    root = ElementTree.parse(path).getroot()
    if any(element.tag.rsplit("}", 1)[-1] != "path" for element in root.iter() if element is not root):
        raise ValueError(f"{path} must contain path elements only")
    svg_path = SVGPath(str(path))
    bounds_pen = BoundsPen(None)
    svg_path.draw(bounds_pen)
    if bounds_pen.bounds is None:
        raise ValueError(f"{path} has no outlines")
    x_min, y_min, x_max, y_max = bounds_pen.bounds
    scale = min(max_width / (x_max - x_min), max_height / (y_max - y_min))
    x_offset = (ADVANCE - (x_max - x_min) * scale) / 2 - x_min * scale
    y_offset = center_y + (y_max - y_min) * scale / 2 + y_min * scale

    glyph_pen = TTGlyphPen(None)
    quadratic_pen = Cu2QuPen(glyph_pen, max_err=1.0, reverse_direction=True)
    transform_pen = TransformPen(quadratic_pen, (scale, 0, 0, -scale, x_offset, y_offset))
    svg_path.draw(transform_pen)
    return glyph_pen.glyph()


def build(output: Path) -> None:
    with (ROOT / "font" / "codepoints.toml").open("rb") as config_file:
        config = tomllib.load(config_file)
    names = list(config["glyphs"])
    if names != list(STABLE_GLYPH_ORDER):
        raise ValueError("codepoint order is part of the stable font contract")
    codepoints = {int(value, 16): name for name, value in config["glyphs"].items()}
    if len(codepoints) != len(names):
        raise ValueError("duplicate codepoint")

    empty_pen = TTGlyphPen(None)
    glyphs = {".notdef": empty_pen.glyph()}
    for name in names:
        glyphs[name] = svg_glyph(ROOT / "assets" / "svg" / f"{name}.svg")

    family = config["family"]
    version = config["version"]
    builder = FontBuilder(UPM, isTTF=True)
    builder.setupGlyphOrder([".notdef", *names])
    builder.setupCharacterMap(codepoints)
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({name: (ADVANCE, 0) for name in glyphs})
    builder.setupHorizontalHeader(ascent=ASCENT, descent=DESCENT, lineGap=0)
    builder.setupNameTable(
        {
            "copyright": "See THIRD_PARTY_NOTICES.md; marks belong to their respective owners.",
            "familyName": family,
            "styleName": "Regular",
            "uniqueFontIdentifier": f"herdr-agent-icons:{version}",
            "fullName": f"{family} Regular",
            "version": f"Version {version}",
            "psName": re.sub(r"[^A-Za-z0-9-]", "", family.replace(" ", "-")) + "-Regular",
            "licenseDescription": "Apache-2.0 and MIT source marks; see bundled THIRD_PARTY_NOTICES.md.",
        }
    )
    builder.setupOS2(
        sTypoAscender=ASCENT,
        sTypoDescender=DESCENT,
        sTypoLineGap=0,
        usWinAscent=ASCENT,
        usWinDescent=-DESCENT,
        sxHeight=500,
        sCapHeight=700,
        xAvgCharWidth=ADVANCE,
        achVendID="HRDR",
        fsType=0,
    )
    builder.setupPost(isFixedPitch=1)
    builder.setupMaxp()
    builder.font["head"].created = FONT_TIMESTAMP
    builder.font["head"].modified = FONT_TIMESTAMP
    output.parent.mkdir(parents=True, exist_ok=True)
    builder.save(output)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "HerdrHarnessLogos-Regular.ttf",
    )
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
