import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from configuration import ghostty_mapping, merge_layout
from setup_sidebar import digest, edited_files, install

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = (ROOT / "sidebar-layout.toml").read_text()
PRIORITY_FRAGMENT = (ROOT / "sidebar-layout-priority.toml").read_text()


class ConfigurationTests(unittest.TestCase):
    def test_merge_preserves_other_settings_and_is_idempotent(self):
        original = '''# personal theme
[theme]
name = "custom"
[ui]
sidebar_width = 42
agent_panel_sort = "priority"
[ui.sidebar.agents]
rows = [["agent"]]
[ui.sidebar.spaces]
rows = [["workspace"]]
[[keys.command]]
key = "prefix+y"
command = "my-action"
'''
        result = merge_layout(original, FRAGMENT)
        parsed = tomllib.loads(result)
        self.assertEqual(parsed["theme"], {"name": "custom"})
        self.assertEqual(parsed["ui"]["sidebar_width"], 42)
        self.assertEqual(parsed["ui"]["sidebar"]["spaces"], {"rows": [["workspace"]]})
        self.assertEqual(parsed["keys"], tomllib.loads(original)["keys"])
        self.assertIn("# personal theme", result)
        self.assertEqual(merge_layout(result, FRAGMENT), result)

    def test_empty_config_is_valid(self):
        result = merge_layout("", FRAGMENT)
        self.assertEqual(tomllib.loads(result)["ui"]["agent_panel_sort"], "spaces")

    def test_priority_layout_sets_priority_sort(self):
        result = merge_layout("[ui]\nagent_panel_sort = \"spaces\"\n", PRIORITY_FRAGMENT, "priority")
        parsed = tomllib.loads(result)
        self.assertEqual(parsed["ui"]["agent_panel_sort"], "priority")
        self.assertIn("$ihs_row_tab", result)
        self.assertIn("$ihs_repo", result)
        self.assertIn("$ihs_row_branch", result)
        self.assertEqual(tomllib.loads(PRIORITY_FRAGMENT), tomllib.loads(FRAGMENT))

    def test_both_layouts_use_native_status_without_color_override(self):
        for fragment in (FRAGMENT, PRIORITY_FRAGMENT):
            agents = tomllib.loads(fragment)["ui"]["sidebar"]["agents"]
            for rows in [agents["rows"], *agents["rows_by_agent"].values()]:
                icons = [token for row in rows for token in row if token["token"] == "state_icon"]
                self.assertEqual(icons, [{"token": "state_icon"}])
                self.assertFalse(any(token["token"] == "$ihs_status" for row in rows for token in row))

    def test_dry_run_install_reports_selected_sort(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = SimpleNamespace(
                config=root / "herdr.toml",
                dry_run=True,
                font_dir=root / "fonts",
                ghostty_config=root / "ghostty",
                json=True,
                sort="priority",
                text=True,
            )
            with patch("setup_sidebar.plugin_info", return_value=None), \
                 patch("setup_sidebar.plugin_config_dir", return_value=root / "plugin"), \
                 patch("setup_sidebar.emit") as emit:
                install(args, "herdr")
            summary = emit.call_args.args[0]
            self.assertEqual(summary["sort"], "priority")
            self.assertIn("priority", " ".join(summary["notes"]))

    def test_unsupported_inline_table_fails_without_changing_input(self):
        original = 'ui = { agent_panel_sort = "priority", sidebar = { agents = { rows = [["agent"]] } } }\n'
        with self.assertRaises(ValueError):
            merge_layout(original, FRAGMENT)

    def test_multiline_string_cannot_silently_lose_data(self):
        original = 'note = """\n[ui.sidebar.agents]\nkeep this text\n"""\n'
        with self.assertRaises(ValueError):
            merge_layout(original, FRAGMENT)

    def test_font_mapping_preserves_existing_settings(self):
        original = "font-size = 16\nkeybind = ctrl+y=copy_to_clipboard\n"
        result = ghostty_mapping(original)
        self.assertTrue(result.startswith(original.rstrip()))
        self.assertEqual(ghostty_mapping(result), result)

    def test_removal_detects_later_edits_and_missing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_bytes(b"installed")
            state = {"files": {str(path): {"installed_sha256": digest(b"installed")}}}
            self.assertEqual(edited_files(state), [])
            path.write_bytes(b"user edit")
            self.assertEqual(edited_files(state), [str(path)])
            path.unlink()
            self.assertEqual(edited_files(state), [str(path)])
