from __future__ import annotations

import tempfile
import tomllib
import unittest
from pathlib import Path

try:
    from fontTools.ttLib import TTFont
except ImportError:  # Build-only checks run in the font virtual environment.
    TTFont = None


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GLYPHS = [
    "claude",
    "codex",
    "opencode",
    "omp",
    "cline",
    "mastracode",
    "kimi",
    "kilo",
    "maki",
]
EXPECTED_CMAP = {0xE1A0 + offset: name for offset, name in enumerate(EXPECTED_GLYPHS)}


class FontSourceTests(unittest.TestCase):
    def test_codepoints_and_svg_sources_match(self) -> None:
        with (ROOT / "font" / "codepoints.toml").open("rb") as config_file:
            glyphs = tomllib.load(config_file)["glyphs"]
        svg_names = {path.stem for path in (ROOT / "assets" / "svg").glob("*.svg")}

        self.assertEqual(list(glyphs), EXPECTED_GLYPHS)
        self.assertEqual([int(value, 16) for value in glyphs.values()], list(EXPECTED_CMAP))
        self.assertEqual(set(glyphs), svg_names)


@unittest.skipIf(TTFont is None, "fontTools is a build-only dependency")
class FontTests(unittest.TestCase):
    def test_sidebar_font_matches_sources(self):
        from tools.build_sidebar_font import build
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sidebar.ttf"
            build(output)
            self.assertEqual(output.read_bytes(), (ROOT / "dist/HerdrSidebarLogos-Regular.ttf").read_bytes())
            font = TTFont(output)
            self.assertEqual(font.getBestCmap(), EXPECTED_CMAP)
            self.assertEqual(font["name"].getDebugName(1), "Herdr Sidebar Logos")
            for name in ("claude", "codex"):
                self.assertEqual(font["hmtx"].metrics[name][0], 600)
                self.assertGreater(font["glyf"][name].numberOfContours, 0)

    def test_committed_font_contract(self) -> None:
        font = TTFont(ROOT / "dist" / "HerdrHarnessLogos-Regular.ttf")
        self.assertTrue(
            {"head", "hhea", "maxp", "OS/2", "hmtx", "cmap", "glyf", "loca", "name", "post"}.issubset(
                font.keys()
            )
        )
        self.assertFalse({"SVG ", "COLR", "CPAL", "CBDT", "fvar"}.intersection(font.keys()))
        cmap = font.getBestCmap()
        self.assertEqual(cmap, EXPECTED_CMAP)
        self.assertEqual(font.getGlyphOrder(), [".notdef", *EXPECTED_GLYPHS])
        self.assertEqual(font["post"].isFixedPitch, 1)
        for name in cmap.values():
            self.assertEqual(font["hmtx"].metrics[name][0], 600)
            self.assertGreater(font["glyf"][name].numberOfContours, 0)

    def test_build_is_deterministic(self) -> None:
        from tools.build_font import build

        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.ttf"
            second = Path(directory) / "second.ttf"
            build(first)
            build(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(
                first.read_bytes(),
                (ROOT / "dist" / "HerdrHarnessLogos-Regular.ttf").read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
