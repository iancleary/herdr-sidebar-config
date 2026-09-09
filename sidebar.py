"""Publish compact task rows from native Herdr facts, only when values change."""
import fcntl
import argparse
import json
import os
import re
import sys
import subprocess
from pathlib import Path
from runtime import PLUGIN_ID, herdr_binary, icon_mode, logo_for, run_herdr
from client_sort import client_sort

STATES = {"working": "◔", "blocked": "?", "done": "✓", "idle": "○", "unknown": "·"}
HISTORY = {
    "codex": (".codex/history.jsonl", "session_id", "text"),
    "claude": (".claude/history.jsonl", "sessionId", "display"),
}
VAGUE = re.compile(
    r"^(yes|okay|ok|go ahead|go on|continue|nice|thank|where we at|are you still|"
    r"how(?:'s| is) it going|also i like)\b",
    re.I,
)


def _task_text(value):
    if not isinstance(value, str):
        return None
    for raw in value.splitlines():
        text = re.sub(r"\s+", " ", raw).strip().lstrip("#>*- ")
        text = re.sub(r"^(?:\[Image #\d+\]\s*)+", "", text, flags=re.I)
        if not text or text.startswith(("AGENTS.md instructions", "<environment_context", "<INSTRUCTIONS", "<skill")):
            continue
        if VAGUE.match(text):
            continue
        text = re.sub(r"^(?:can|could|would) (?:you|we) (?:please )?", "", text, flags=re.I)
        return text[:96].rstrip(" ,.;:-")
    return None


def _reverse_history(path, max_bytes=512 * 1024):
    try:
        with path.open("rb") as stream:
            end = stream.seek(0, os.SEEK_END)
            start = max(0, end - max_bytes)
            stream.seek(start)
            data = stream.read()
    except OSError:
        return
    if start:
        data = data.split(b"\n", 1)[-1]
    for raw in reversed(data.splitlines()):
        yield raw.decode("utf-8", "replace")


def latest_history_task(pane):
    source = HISTORY.get(pane.get("agent"))
    session = pane.get("agent_session") or {}
    session_id = session.get("value") if isinstance(session, dict) else None
    if not source or not session_id:
        return None
    relative_path, session_key, text_key = source
    for line in _reverse_history(Path.home() / relative_path):
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if record.get(session_key) != session_id:
            continue
        text = _task_text(record.get(text_key))
        if text:
            return text
    return None


def task_label(pane, tabs):
    tokens = pane.get("tokens") or {}
    if tokens.get("ihs_title"):
        return tokens["ihs_title"]
    if pane.get("agent_status") == "working":
        task = latest_history_task(pane)
        if task:
            return task[:1].upper() + task[1:]
    raw = pane.get("terminal_title_stripped") or ""
    parts = [p.strip().rstrip(".… ") for p in raw.split(" | ")]
    candidates = [p for p in parts if p and not p.startswith(("[", "~/", "/", "<"))
                  and not re.match(r"^[A-Za-z]:[/\\]", p)]
    # Claude's named session is more durable than its transient prompt snippets.
    if candidates and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+){2,}", candidates[0]):
        return candidates[0].replace("-", " ").capitalize()
    for text in reversed(candidates):
        if not VAGUE.match(text):
            text = re.sub(r"^(?:can|could|would) (?:you|we) (?:please )?", "", text, flags=re.I)
            return text[:1].upper() + text[1:]
    tab = tabs.get(pane.get("tab_id"), "")
    if tab and tab not in {"main", "shell"} and not re.fullmatch(r"(?:💤\s*)?\d+", tab):
        return tab.replace("-", " ")
    name = pane.get("name") or pane.get("label")
    if name:
        return name.replace("-", " ")
    return {"agy": "AGY session", "codex": "Codex session", "claude": "Claude session"}.get(
        pane.get("agent"), f"{pane.get('agent', 'Agent')} session")


def compact_branch_label(value):
    if not value:
        return None
    return value.removeprefix("worktree/") or value


def workspace_context(workspace):
    worktree = workspace.get("worktree") or {}
    repo_key = worktree.get("repo_key") or workspace["workspace_id"]
    repo = worktree.get("repo_name") or workspace.get("label") or "workspace"
    # A workspace label identifies the checkout; it is not a guessed Git branch.
    branch = workspace.get("branch") or workspace.get("label") or workspace["workspace_id"]
    return {"repo_key": repo_key, "repo": repo, "branch": branch}


def with_checkout_branches(workspaces, panes=()):
    """Read branch identity once per checkout per refresh, without guessing paths."""
    branches = {}
    result = []
    for workspace in workspaces:
        path = (workspace.get("worktree") or {}).get("checkout_path")
        if not path:
            directories = {p["cwd"] for p in panes
                           if p.get("workspace_id") == workspace["workspace_id"]
                           and p.get("cwd") and Path(p["cwd"]).is_absolute()}
            # Older/plain workspaces may not expose worktree provenance.
            # Use native cwd only when it identifies one unambiguous checkout.
            if len(directories) == 1:
                path = directories.pop()
        branch = workspace.get("branch")
        if not branch and path and Path(path).is_absolute():
            if path not in branches:
                try:
                    proc = subprocess.run(
                        ["git", "-C", path, "symbolic-ref", "--quiet", "--short", "HEAD"],
                        capture_output=True, text=True, timeout=2,
                    )
                    branches[path] = proc.stdout.strip() if proc.returncode == 0 else None
                except (OSError, subprocess.TimeoutExpired):
                    branches[path] = None
            branch = branches[path]
        result.append({**workspace, "branch": branch})
    return result


def desired_headers(panes, workspaces):
    contexts = {w["workspace_id"]: workspace_context(w) for w in workspaces}
    seen = set()
    result = {}
    for pane in panes:
        workspace = pane["workspace_id"]
        repo = branch = None
        if pane.get("agent"):
            context = contexts.get(workspace, {"repo_key": workspace, "repo": workspace, "branch": None})
            repo_key = context["repo_key"]
            if repo_key not in seen:
                repo = context["repo"]
                seen.add(repo_key)
            branch_key = (repo_key, workspace)
            if branch_key not in seen and context["branch"]:
                branch = context["branch"]
                seen.add(branch_key)
        result[pane["pane_id"]] = {"repo": repo, "branch": branch}
    return result


def desired_rows(panes, workspaces, tabs, icons="font", sort="spaces"):
    headers = desired_headers(panes, workspaces)
    contexts = {w["workspace_id"]: workspace_context(w) for w in workspaces}
    # Follow native pane order: the plugin cannot reorder Herdr's agent panel.
    # Restart a heading if a family appears again after another family.
    agents = [pane for pane in panes if pane.get("agent")]
    priority_grouping = sort == "priority" and all(
        isinstance(pane.get("state_change_seq"), int) for pane in agents)
    if priority_grouping:
        # Match Herdr's stable status-descending, recency-descending ordering.
        ranks = {"blocked": 4, "done": 3, "working": 2, "idle": 1, "unknown": 0}
        agents.sort(key=lambda pane: (
            -ranks.get(pane.get("agent_status"), 0), -pane["state_change_seq"],
            pane.get("_agent_order", panes.index(pane)),
        ))
    position = {pane["pane_id"]: index for index, pane in enumerate(agents)}
    result = {}
    for pane in panes:
        heading = headers[pane["pane_id"]]
        values = {"ihs_group": None, "ihs_repo": heading["repo"], "ihs_branch": heading["branch"],
                  "ihs_tab": None, "ihs_gap": None, "ihs_logo": None,
                  "ihs_tab_context": None, "ihs_context": None,
                  "ihs_row_logo": None, "ihs_status": None, "ihs_space_title": None,
                  "ihs_row_branch": None, "ihs_row_tab": None}
        values.update({f"ihs_{state}": None for state in STATES})
        if pane.get("agent"):
            tab_id = pane.get("tab_id")
            context = contexts.get(pane["workspace_id"], {})
            logo = logo_for(pane["agent"], icons)
            index = position[pane["pane_id"]]
            previous = agents[index - 1] if index else None
            same_workspace = previous and previous["workspace_id"] == pane["workspace_id"]
            previous_context = contexts.get(previous["workspace_id"], {}) if previous else {}
            same_family = previous and previous_context.get("repo_key") == context.get("repo_key")
            values["ihs_repo"] = None if same_family else context.get("repo")
            branch_label = context.get("branch", pane["workspace_id"])
            values["ihs_branch"] = None if same_workspace or branch_label == context.get("repo") else branch_label
            # Keep the logo free of tree guides so priority layout stays flat.
            values["ihs_logo"] = logo
            tab_label = tabs.get(tab_id) or "tab"
            values["ihs_tab_context"] = tab_label + " ·"
            # Herdr indents the first visible row by 1 cell, later rows by 3.
            # U+2800 survives metadata trimming; the local Complete font maps
            # it to the ordinary space glyph. Only heading-less rows need it.
            if not values["ihs_repo"] and not values["ihs_branch"]:
                values["ihs_tab_context"] = "\u2800\u2800" + values["ihs_tab_context"]
            # Linked worktrees sit two cells deeper than their parent checkout.
            linked = bool(next((w.get("worktree", {}).get("is_linked_worktree")
                                for w in workspaces if w["workspace_id"] == pane["workspace_id"]
                                and w.get("worktree")), False))
            workspace = next((w for w in workspaces
                              if w["workspace_id"] == pane["workspace_id"]), {})
            branch = workspace.get("branch")
            same_branch = same_family and previous_context.get("branch") == branch
            if branch and not same_branch:
                values["ihs_row_branch"] = ("" if values["ihs_repo"] else "\u2800\u2800") + "╰─ " + compact_branch_label(branch)
            has_heading = bool(values["ihs_repo"] or values["ihs_row_branch"])
            padding = (0 if has_heading else 2) + (2 if branch or linked else 0)
            values["ihs_row_logo"] = "\u2800" * padding + logo
            if linked and values["ihs_branch"] and not values["ihs_repo"]:
                values["ihs_branch"] = "\u2800\u2800" + values["ihs_branch"]
            priority_context = list(dict.fromkeys([context.get("repo"), context.get("branch"), tab_label]))
            values["ihs_context"] = " · ".join(part for part in priority_context if part)
            status = pane.get("agent_status", "unknown")
            if status not in STATES:
                status = "unknown"
            values[f"ihs_{status}"] = STATES[status] + " " + task_label(pane, tabs)
            values["ihs_status"] = {"working": "◔", "blocked": "●", "done": "●",
                                    "idle": "○", "unknown": "○"}[status]
            values["ihs_space_title"] = context.get("repo") or pane["workspace_id"]
            values["ihs_row_tab"] = tab_label
            if sort == "priority" and not priority_grouping:
                # Priority moves whole agent blocks. Never borrow a heading
                # from another agent: its position can change independently.
                values["ihs_repo"] = context.get("repo") or pane["workspace_id"]
                values["ihs_row_branch"] = "╰─ " + compact_branch_label(branch) if branch else None
                values["ihs_row_logo"] = ("\u2800\u2800" if branch else "") + logo
        result[pane["pane_id"]] = values
    return result


def changed_tokens(existing, desired):
    return {key: value for key, value in desired.items() if existing.get(key) != value}


def main():
    parser = argparse.ArgumentParser(description="Refresh the Herdr workspace/tab/agent sidebar.")
    parser.add_argument("--clear", action="store_true", help="clear this plugin's display tokens")
    args = parser.parse_args()
    if not os.environ.get("HERDR_PLUGIN_STATE_DIR"):
        raise RuntimeError("Run through Herdr: herdr plugin action invoke refresh --plugin " + PLUGIN_ID)
    state = Path(os.environ["HERDR_PLUGIN_STATE_DIR"])
    state.mkdir(parents=True, exist_ok=True)
    with (state / "group-headers.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        herdr = herdr_binary()
        snapshot = run_herdr(herdr, "api", "snapshot")["result"]["snapshot"]
        # agent.list distinguishes an unseen completion (done) from idle.
        agents = {a["pane_id"]: {**a, "_agent_order": i}
                  for i, a in enumerate(snapshot["agents"])}
        panes = [{**p, **agents.get(p["pane_id"], {})} for p in snapshot["panes"]]
        workspaces = with_checkout_branches(snapshot["workspaces"], panes)
        tabs = {t["tab_id"]: t["label"] for t in snapshot["tabs"]}
        desired = desired_rows(panes, workspaces, tabs, icon_mode(), sort=client_sort())
        if args.clear:
            desired = {pane_id: dict.fromkeys(values) for pane_id, values in desired.items()}
        source = "plugin:" + os.environ.get("HERDR_PLUGIN_ID", PLUGIN_ID)
        for pane in panes:
            changes = changed_tokens(pane.get("tokens") or {}, desired[pane["pane_id"]])
            if not changes:
                continue
            args = ["pane", "report-metadata", pane["pane_id"], "--source", source]
            for key, value in changes.items():
                args += ["--token", key + "=" + value] if value is not None else ["--clear-token", key]
            run_herdr(herdr, *args)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError) as error:
        print(f"Herdr Sidebar: {error}", file=sys.stderr)
        sys.exit(1)
