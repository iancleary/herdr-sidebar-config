"""Single-local-client sort preferences; unknown state uses self-contained rows."""
import json
import os
from pathlib import Path


def client_sort(state_root=None):
    root = Path(state_root) if state_root else Path(
        os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "herdr"
    paths = list((root / "client-shell").glob("local-*.json"))
    if len(paths) != 1:
        return "priority"
    try:
        mode = json.loads(paths[0].read_text()).get("agent_panel_sort")
    except (OSError, ValueError, AttributeError):
        return "priority"
    return "spaces" if mode == "spaces" else "priority"
