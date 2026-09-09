import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from sidebar import task_label, desired_rows, changed_tokens, with_checkout_branches
import subprocess


class SidebarRowsTests(unittest.TestCase):
    def test_plain_workspace_displays_default_branches_from_native_cwd(self):
        panes = [{"pane_id": "p", "workspace_id": "w", "agent": "codex", "cwd": "/repo"}]
        for branch in ("main", "master", "default"):
            with self.subTest(branch=branch), patch("sidebar.subprocess.run", return_value=
                    subprocess.CompletedProcess([], 0, branch + "\n")) as run:
                spaces = with_checkout_branches([{"workspace_id": "w", "label": "repo"}], panes)
            self.assertEqual(run.call_args.args[0][2], "/repo")
            for mode in ("spaces", "priority"):
                self.assertEqual(desired_rows(panes, spaces, {}, sort=mode)["p"]["ihs_row_branch"],
                                 "╰─ " + branch)

    def test_conflicting_pane_directories_do_not_guess_workspace_branch(self):
        panes = [{"workspace_id": "w", "cwd": path} for path in ("/one", "/two")]
        with patch("sidebar.subprocess.run") as run:
            spaces = with_checkout_branches([{"workspace_id": "w", "label": "repo"}], panes)
        run.assert_not_called()
        self.assertIsNone(spaces[0]["branch"])

    def test_working_agent_uses_latest_meaningful_codex_task(self):
        with tempfile.TemporaryDirectory() as tmp:
            history = Path(tmp) / ".codex" / "history.jsonl"
            history.parent.mkdir()
            history.write_text("\n".join([
                json.dumps({
                    "session_id": "session-1",
                    "ts": 1,
                    "text": "[Image #1] Integrate the worker commits and run the installed Mac acceptance.",
                }),
                "not valid json",
                json.dumps({
                    "session_id": "session-1",
                    "ts": 2,
                    "text": "How's it going?",
                }),
            ]) + "\n")
            pane = {
                "agent": "codex",
                "agent_status": "working",
                "terminal_title_stripped": "augmented-wolf",
                "agent_session": {"kind": "id", "value": "session-1"},
            }
            with patch("sidebar.Path.home", return_value=Path(tmp)):
                self.assertEqual(
                    task_label(pane, {}),
                    "Integrate the worker commits and run the installed Mac acceptance",
                )

    def test_task_ignores_session_path_and_vague_followup(self):
        pane = {"agent": "codex", "terminal_title_stripped":
                "[33] ~/Work/project | Review the launch flow | are you still on …"}
        self.assertEqual(task_label(pane, {}), "Review the launch flow")

    def test_named_session_beats_notification_markup(self):
        pane = {"agent": "claude", "terminal_title_stripped":
                "sidebar-layout-review | [71] ~/Work/project | <task-notification> stuff"}
        self.assertEqual(task_label(pane, {}), "Sidebar layout review")

    def test_paths_never_become_task_labels(self):
        pane = {"agent": "agy", "terminal_title_stripped": "[3] ~/Work/project"}
        self.assertEqual(task_label(pane, {}), "AGY session")

    def test_rows_keep_live_state_without_blank_group_gap(self):
        panes = [
            {"pane_id": "w1:p1", "workspace_id": "w1", "agent": "codex", "agent_status": "working"},
            {"pane_id": "w1:p2", "workspace_id": "w1", "agent": "claude", "agent_status": "blocked"},
            {"pane_id": "w2:p1", "workspace_id": "w2", "agent": "codex", "agent_status": "done"},
        ]
        rows = desired_rows(panes, [{"workspace_id": "w1", "label": "one"},
                                    {"workspace_id": "w2", "label": "two"}], {})
        self.assertIsNone(rows["w1:p1"]["ihs_gap"])
        self.assertEqual(rows["w1:p1"]["ihs_repo"], "one")
        self.assertIsNone(rows["w1:p1"]["ihs_group"])
        self.assertIsNone(rows["w1:p1"]["ihs_branch"])
        self.assertIsNone(rows["w1:p2"]["ihs_group"])
        self.assertIsNone(rows["w1:p2"]["ihs_repo"])
        self.assertIsNone(rows["w1:p2"]["ihs_gap"])
        self.assertIsNone(rows["w2:p1"]["ihs_gap"])
        self.assertEqual(rows["w2:p1"]["ihs_repo"], "two")
        self.assertTrue(rows["w1:p1"]["ihs_working"].startswith("◔ "))
        self.assertTrue(rows["w1:p2"]["ihs_blocked"].startswith("? "))
        self.assertTrue(rows["w2:p1"]["ihs_done"].startswith("✓ "))
        self.assertIsNone(rows["w2:p1"]["ihs_working"])

    def test_unchanged_rows_do_not_publish_again(self):
        desired = {"ihs_group": "project", "ihs_working": "⠿ Review", "ihs_done": None}
        existing = {"ihs_group": "project", "ihs_working": "⠿ Review"}
        self.assertEqual(changed_tokens(existing, desired), {})

    def test_tab_groups_use_compact_tree_guides(self):
        panes = [
            {"pane_id": "w1:p1", "workspace_id": "w1", "tab_id": "w1:t1", "agent": "codex"},
            {"pane_id": "w1:p2", "workspace_id": "w1", "tab_id": "w1:t1", "agent": "claude"},
            {"pane_id": "w1:p3", "workspace_id": "w1", "tab_id": "w1:t2", "agent": "codex"},
        ]
        workspaces = [{"workspace_id": "w1", "label": "project"}]
        rows = desired_rows(panes, workspaces, {"w1:t1": "main", "w1:t2": "docs"})
        self.assertIsNone(rows["w1:p1"]["ihs_tab"])
        self.assertIsNone(rows["w1:p2"]["ihs_tab"])
        self.assertIsNone(rows["w1:p3"]["ihs_tab"])
        self.assertEqual(rows["w1:p1"]["ihs_repo"], "project")
        self.assertIsNone(rows["w1:p2"]["ihs_repo"])
        self.assertIsNone(rows["w1:p3"]["ihs_repo"])
        self.assertEqual(rows["w1:p1"]["ihs_logo"], "\ue1a1")
        self.assertEqual(rows["w1:p2"]["ihs_logo"], "\ue1a0")
        self.assertEqual(rows["w1:p3"]["ihs_logo"], "\ue1a1")
        self.assertEqual(rows["w1:p1"]["ihs_tab_context"], "main ·")
        self.assertEqual(rows["w1:p2"]["ihs_tab_context"], "\u2800\u2800main ·")
        self.assertEqual(rows["w1:p3"]["ihs_tab_context"], "\u2800\u2800docs ·")
        self.assertTrue(rows["w1:p1"]["ihs_context"].startswith("project · main"))
        self.assertTrue(rows["w1:p1"]["ihs_unknown"].startswith("· "))
        self.assertTrue(rows["w1:p2"]["ihs_unknown"].startswith("· "))
        self.assertTrue(rows["w1:p3"]["ihs_unknown"].startswith("· "))

        # A close/move clears the former heading and updates the remaining branch.
        panes[0].pop("agent")
        panes[2]["tab_id"] = "w1:t1"
        rows = desired_rows(panes, workspaces, {"w1:t1": "renamed"})
        self.assertIsNone(rows["w1:p1"]["ihs_tab"])
        self.assertEqual(rows["w1:p2"]["ihs_repo"], "project")
        self.assertIsNone(rows["w1:p2"]["ihs_tab"])
        self.assertIsNone(rows["w1:p3"]["ihs_tab"])
        self.assertEqual(rows["w1:p2"]["ihs_logo"], "\ue1a0")
        self.assertEqual(rows["w1:p3"]["ihs_logo"], "\ue1a1")

    def test_single_tab_keeps_hierarchy_when_shell_tab_added(self):
        panes = [
            {"pane_id": "w1:p1", "workspace_id": "w1", "tab_id": "w1:t1", "agent": "codex"},
            {"pane_id": "w1:p2", "workspace_id": "w1", "tab_id": "w1:t1", "agent": "claude"},
        ]
        workspaces = [{"workspace_id": "w1", "label": "project"}]
        tabs = {"w1:t1": "named-tab", "w1:t2": "shell"}
        compact = desired_rows(panes, workspaces, tabs)
        self.assertTrue(all(row["ihs_tab"] is None for row in compact.values()))
        self.assertEqual(compact["w1:p1"]["ihs_logo"], "\ue1a1")
        self.assertEqual(compact["w1:p2"]["ihs_logo"], "\ue1a0")
        self.assertEqual(compact["w1:p1"]["ihs_tab_context"], "named-tab ·")
        self.assertNotIn("named-tab", compact["w1:p1"]["ihs_unknown"])

        # Count real tabs, including shell-only tabs, so tab identity stays useful.
        panes.append({"pane_id": "w1:p3", "workspace_id": "w1", "tab_id": "w1:t2"})
        expanded = desired_rows(panes, workspaces, tabs)
        self.assertIsNone(expanded["w1:p1"]["ihs_tab"])
        self.assertEqual(expanded["w1:p1"]["ihs_tab_context"], "named-tab ·")
        self.assertTrue(expanded["w1:p1"]["ihs_context"].startswith("project · named-tab"))
        self.assertIsNone(expanded["w1:p3"]["ihs_tab"])
        self.assertEqual(desired_rows(panes[:-1], workspaces, tabs), compact)

    def test_worktree_context_tokens_group_repo_and_branch(self):
        panes = [
            {"pane_id": "w1:p1", "workspace_id": "w1", "tab_id": "w1:t1", "agent": "codex"},
            {"pane_id": "w2:p1", "workspace_id": "w2", "tab_id": "w2:t1", "agent": "claude"},
        ]
        workspaces = [
            {"workspace_id": "w1", "label": "repo", "worktree": {
                "repo_key": "/repo/.git", "repo_name": "repo", "repo_root": "/repo",
                "checkout_path": "/repo", "is_linked_worktree": False}},
            {"workspace_id": "w2", "label": "worktree/feature", "worktree": {
                "repo_key": "/repo/.git", "repo_name": "repo", "repo_root": "/repo",
                "checkout_path": "/worktrees/repo/feature", "is_linked_worktree": True}},
        ]
        rows = desired_rows(panes, workspaces, {"w1:t1": "main", "w2:t1": "main"})
        self.assertEqual(rows["w1:p1"]["ihs_repo"], "repo")
        self.assertIsNone(rows["w1:p1"]["ihs_branch"])
        self.assertIsNone(rows["w2:p1"]["ihs_repo"])
        self.assertEqual(rows["w2:p1"]["ihs_branch"], "\u2800\u2800worktree/feature")
        self.assertEqual(rows["w2:p1"]["ihs_context"], "repo · worktree/feature · main")
        self.assertEqual(rows["w1:p1"]["ihs_row_logo"], "\ue1a1")
        self.assertEqual(rows["w2:p1"]["ihs_row_logo"], "\u2800\u2800\u2800\u2800\ue1a0")
        self.assertEqual(rows["w2:p1"]["ihs_space_title"], "repo")
        self.assertEqual(rows["w2:p1"]["ihs_status"], "○")

    def test_curved_branch_rows_keep_sibling_agents_aligned(self):
        spaces = [{"workspace_id": "w", "label": "checkout-label", "branch": "worktree/feature",
                   "worktree": {"repo_name": "repo", "is_linked_worktree": True}}]
        panes = [{"pane_id": str(i), "workspace_id": "w", "agent": "codex"} for i in range(3)]
        rows = desired_rows(panes, spaces, {})
        for i, values in enumerate(rows.values()):
            self.assertEqual(values["ihs_space_title"], "repo")
            self.assertEqual(values["ihs_row_branch"], "╰─ feature" if i == 0 else None)
            native_indent = 3 if i == 0 else 1
            padding = len(values["ihs_row_logo"]) - len(values["ihs_row_logo"].lstrip("\u2800"))
            self.assertEqual(native_indent + padding, 5)

    def test_branch_group_shows_repo_once_and_keeps_tab_titles(self):
        spaces = [{"workspace_id": "w", "label": "repo", "branch": "main"}]
        panes = [{"pane_id": str(i), "workspace_id": "w", "tab_id": str(i), "agent": "codex"}
                 for i in range(3)]
        rows = list(desired_rows(panes, spaces, {"0": "1 · Review", "1": "2 · Build", "2": "3"}).values())
        self.assertEqual([r["ihs_repo"] for r in rows], ["repo", None, None])
        self.assertEqual([r["ihs_row_branch"] for r in rows], ["╰─ main", None, None])
        self.assertEqual([r["ihs_row_tab"] for r in rows], ["1 · Review", "2 · Build", "3"])

    def test_branch_lookup_uses_git_and_caches_checkout(self):
        spaces = [{"workspace_id": str(i), "label": "not-a-branch",
                   "worktree": {"checkout_path": "/repo"}} for i in range(2)]
        with patch("sidebar.subprocess.run", return_value=subprocess.CompletedProcess([], 0, "feature/real\n")) as run:
            resolved = with_checkout_branches(spaces)
        self.assertEqual([w["branch"] for w in resolved], ["feature/real"] * 2)
        run.assert_called_once_with(["git", "-C", "/repo", "symbolic-ref", "--quiet", "--short", "HEAD"],
                                    capture_output=True, text=True, timeout=2)

    def test_unavailable_branch_is_not_invented(self):
        spaces = [{"workspace_id": "w", "label": "not-a-branch", "worktree": {"checkout_path": "/repo"}}]
        for outcome in (OSError(), subprocess.TimeoutExpired("git", 2)):
            with patch("sidebar.subprocess.run", side_effect=outcome):
                resolved = with_checkout_branches(spaces)
            self.assertIsNone(resolved[0]["branch"])
            rows = desired_rows([{"pane_id": "p", "workspace_id": "w", "agent": "codex"}], resolved, {})
            self.assertIsNone(rows["p"]["ihs_row_branch"])

    def test_blank_padding_only_compensates_headingless_rows(self):
        panes = [
            {"pane_id": "w1:p1", "workspace_id": "w1", "tab_id": "w1:t1", "agent": "codex"},
            {"pane_id": "w1:p2", "workspace_id": "w1", "tab_id": "w1:t1", "agent": "claude"},
            {"pane_id": "w2:p1", "workspace_id": "w2", "tab_id": "w2:t1", "agent": "codex"},
        ]
        rows = desired_rows(panes, [{"workspace_id": "w1", "label": "one"},
                                    {"workspace_id": "w2", "label": "two"}], {"w1:t1": "main"})
        for values in rows.values():
            for key, value in values.items():
                if value is not None:
                    if key in {"ihs_tab_context", "ihs_row_logo"} and not values["ihs_repo"] and not values["ihs_branch"]:
                        self.assertTrue(value.startswith("\u2800\u2800"))
                        self.assertNotIn("\u2800", value[2:])
                    else:
                        self.assertNotIn("\u2800", value)
