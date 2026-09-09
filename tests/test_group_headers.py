import unittest
from sidebar import desired_headers, desired_rows

class GroupHeadersTests(unittest.TestCase):
    def test_family_tree_uses_provenance_and_restarts_after_other_family(self):
        workspaces = [
            {"workspace_id": "a", "label": "checkout", "worktree": {
                "repo_key": "repo-A", "repo_name": "shared-name"}},
            {"workspace_id": "b", "label": "feature", "branch": "feature/api", "worktree": {
                "repo_key": "repo-A", "repo_name": "shared-name"}},
            {"workspace_id": "c", "label": "unrelated", "worktree": {
                "repo_key": "repo-B", "repo_name": "shared-name"}},
        ]
        panes = [
            {"pane_id": "1", "workspace_id": "a", "tab_id": "t1", "agent": "codex"},
            {"pane_id": "2", "workspace_id": "a", "tab_id": "t2", "agent": "claude"},
            {"pane_id": "3", "workspace_id": "b", "tab_id": "t3", "agent": "codex"},
            {"pane_id": "4", "workspace_id": "c", "tab_id": "t4", "agent": "codex"},
            {"pane_id": "5", "workspace_id": "b", "tab_id": "t3", "agent": "codex"},
        ]
        rows = desired_rows(panes, workspaces, {"t1": "1", "t2": "2", "t3": "1", "t4": "1"})
        self.assertEqual(rows["1"]["ihs_repo"], "shared-name")
        self.assertEqual(rows["1"]["ihs_branch"], "checkout")
        self.assertEqual(rows["1"]["ihs_tab_context"], "1 ·")
        self.assertEqual(rows["2"]["ihs_tab_context"], "\u2800\u28002 ·")
        self.assertIsNone(rows["2"]["ihs_branch"])
        self.assertIsNone(rows["3"]["ihs_repo"])
        self.assertEqual(rows["3"]["ihs_branch"], "feature/api")
        self.assertEqual(rows["4"]["ihs_repo"], "shared-name")
        self.assertEqual(rows["5"]["ihs_repo"], "shared-name")
        panes[1].pop("agent")
        updated = desired_rows(panes, workspaces, {})
        self.assertEqual(updated["1"]["ihs_tab_context"], "tab ·")
        self.assertTrue(all(value is None for value in updated["2"].values()))

    def test_headers_follow_first_live_agent_and_clear_former_header(self):
        workspaces = [{"workspace_id": "w1", "label": "project"}]
        panes = [{"pane_id": "w1:p1", "workspace_id": "w1"},
                 {"pane_id": "w1:p2", "workspace_id": "w1", "agent": "codex"},
                 {"pane_id": "w1:p3", "workspace_id": "w1", "agent": "claude"}]
        self.assertEqual(desired_headers(panes, workspaces), {
            "w1:p1": {"repo": None, "branch": None},
            "w1:p2": {"repo": "project", "branch": "project"},
            "w1:p3": {"repo": None, "branch": None}})
        panes[1].pop("agent")
        workspaces[0]["label"] = "renamed"
        self.assertEqual(desired_headers(panes, workspaces), {
            "w1:p1": {"repo": None, "branch": None},
            "w1:p2": {"repo": None, "branch": None},
            "w1:p3": {"repo": "renamed", "branch": "renamed"}})

    def test_worktree_members_share_repo_header_and_get_branch_headers(self):
        workspaces = [
            {"workspace_id": "w1", "label": "repo", "worktree": {
                "repo_key": "/repo/.git", "repo_name": "repo", "repo_root": "/repo",
                "checkout_path": "/repo", "is_linked_worktree": False}},
            {"workspace_id": "w2", "label": "feature", "worktree": {
                "repo_key": "/repo/.git", "repo_name": "repo", "repo_root": "/repo",
                "checkout_path": "/worktrees/repo/feature", "is_linked_worktree": True}},
        ]
        panes = [
            {"pane_id": "w1:p1", "workspace_id": "w1", "agent": "codex"},
            {"pane_id": "w2:p1", "workspace_id": "w2", "agent": "claude"},
        ]
        self.assertEqual(desired_headers(panes, workspaces), {
            "w1:p1": {"repo": "repo", "branch": "repo"},
            "w2:p1": {"repo": None, "branch": "feature"},
        })
