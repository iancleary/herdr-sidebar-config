import json
import tempfile
import unittest
from pathlib import Path

from client_sort import client_sort
from sidebar import desired_rows


class ClientSortTests(unittest.TestCase):
    def test_priority_collapses_adjacent_runs_and_repeats_after_other_space(self):
        spaces = [{"workspace_id": "a", "label": "one", "branch": "main"},
                  {"workspace_id": "b", "label": "two", "branch": "feature"}]
        # Native order is A,A,A,B; priority order is A,A,B,A.
        panes = [{"pane_id": str(i), "workspace_id": ws, "agent": "codex",
                  "agent_status": "idle", "state_change_seq": seq, "tab_id": str(i)}
                 for i, (ws, seq) in enumerate([("a", 40), ("a", 30), ("a", 10), ("b", 20)])]
        rows = desired_rows(panes, spaces, {str(i): str(i) for i in range(4)}, sort="priority")
        self.assertEqual([rows[i]["ihs_repo"] for i in ("0", "1", "3", "2")],
                         ["one", None, "two", "one"])
        self.assertEqual([rows[i]["ihs_row_branch"] for i in ("0", "1", "3", "2")],
                         ["╰─ main", None, "╰─ feature", "╰─ main"])
        for i in ("0", "1", "3", "2"):
            row = rows[i]
            offset = 3 if row["ihs_repo"] else 1
            padding = len(row["ihs_row_logo"]) - len(row["ihs_row_logo"].lstrip("\u2800"))
            self.assertEqual(offset + padding, 5)
        # A status change moves the last A to the top; headings follow it.
        panes[2]["agent_status"] = "blocked"
        changed = desired_rows(panes, spaces, {}, sort="priority")
        self.assertEqual(changed["2"]["ihs_repo"], "one")
        self.assertIsNone(changed["0"]["ihs_repo"])
        self.assertIsNone(changed["1"]["ihs_repo"])
        self.assertEqual(changed["3"]["ihs_repo"], "two")

    def test_atomic_preference_replacement_and_invalid_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            folder = root / "client-shell"
            folder.mkdir()
            path = folder / "local-test.json"
            self.assertEqual(client_sort(root), "priority")
            for mode in ("spaces", "priority", "spaces"):
                pending = folder / "local-test.json.tmp"
                pending.write_text(json.dumps({"agent_panel_sort": mode}))
                pending.replace(path)
                self.assertEqual(client_sort(root), mode)
            path.write_text("{")
            self.assertEqual(client_sort(root), "priority")
            path.write_text('{"agent_panel_sort":"spaces"}')
            (folder / "local-other.json").write_text('{}')
            self.assertEqual(client_sort(root), "priority")

    def test_priority_blocks_keep_context_when_reordered(self):
        spaces = [{"workspace_id": "a", "label": "one", "branch": "main"},
                  {"workspace_id": "b", "label": "two", "branch": "feature"}]
        panes = [{"pane_id": "1", "workspace_id": "a", "agent": "codex", "tab_id": "t1"},
                 {"pane_id": "2", "workspace_id": "a", "agent": "claude", "tab_id": "t2"},
                 {"pane_id": "3", "workspace_id": "b", "agent": "codex", "tab_id": "t3"}]
        tabs = {"t1": "Review", "t2": "Build", "t3": "Test"}
        rows = desired_rows(panes, spaces, tabs, sort="priority")
        reordered = desired_rows([panes[2], panes[1], panes[0]], spaces, tabs, sort="priority")
        for pane in panes:
            for token in ("ihs_repo", "ihs_row_branch", "ihs_row_logo", "ihs_status", "ihs_row_tab"):
                self.assertEqual(rows[pane["pane_id"]][token], reordered[pane["pane_id"]][token])
        self.assertEqual(rows["2"]["ihs_repo"], "one")
        self.assertEqual(rows["2"]["ihs_row_branch"], "╰─ main")
        self.assertEqual(rows["2"]["ihs_row_tab"], "Build")
        grouped = desired_rows(panes, spaces, tabs, sort="spaces")
        self.assertIsNone(grouped["2"]["ihs_repo"])
        self.assertIsNone(grouped["2"]["ihs_row_branch"])
