import unittest
from sidebar import desired_headers

class GroupHeadersTests(unittest.TestCase):
    def test_headers_follow_first_live_agent_and_clear_former_header(self):
        workspaces = [{"workspace_id": "w1", "label": "project"}]
        panes = [{"pane_id": "w1:p1", "workspace_id": "w1"},
                 {"pane_id": "w1:p2", "workspace_id": "w1", "agent": "codex"},
                 {"pane_id": "w1:p3", "workspace_id": "w1", "agent": "claude"}]
        self.assertEqual(desired_headers(panes, workspaces), {
            "w1:p1": None, "w1:p2": "project", "w1:p3": None})
        panes[1].pop("agent")
        workspaces[0]["label"] = "renamed"
        self.assertEqual(desired_headers(panes, workspaces), {
            "w1:p1": None, "w1:p2": None, "w1:p3": "renamed"})
