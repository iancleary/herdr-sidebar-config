"""Edit only the sidebar tables; verify the parsed result before any write."""
from __future__ import annotations

import copy
import re
import tomllib

HEADERS = re.compile(r"(?m)^[ \t]*(\[\[?[^\]\n]+\]\]?)[ \t]*(?:#.*)?$")


def sections(text):
    matches = list(HEADERS.finditer(text))
    return [(m.start(), matches[i + 1].start() if i + 1 < len(matches) else len(text),
             m.group(1).strip("[]").strip()) for i, m in enumerate(matches)]


def merge_layout(text, fragment):
    before = tomllib.loads(text)
    layout = tomllib.loads(fragment)["ui"]["sidebar"]["agents"]
    expected = copy.deepcopy(before)
    ui = expected.setdefault("ui", {})
    ui["agent_panel_sort"] = "spaces"
    ui.setdefault("sidebar", {})["agents"] = layout
    if before == expected:
        return text

    # Keep unrelated tables, comments, keybindings, and terminal settings intact.
    result = text
    for start, end, name in reversed(sections(text)):
        if name == "ui.sidebar.agents" or name.startswith("ui.sidebar.agents."):
            result = result[:start] + result[end:]
    ui_section = next(((a, b) for a, b, name in sections(result) if name == "ui"), None)
    if ui_section:
        start, end = ui_section
        block = result[start:end]
        setting = re.compile(r'(?m)^[ \t]*agent_panel_sort[ \t]*=.*$')
        if setting.search(block):
            block = setting.sub('agent_panel_sort = "spaces"', block)
        else:
            newline = block.find("\n")
            if newline < 0:
                block += '\nagent_panel_sort = "spaces"\n'
            else:
                block = block[:newline + 1] + 'agent_panel_sort = "spaces"\n' + block[newline + 1:]
        result = result[:start] + block + result[end:]
    else:
        result = result.rstrip() + '\n\n[ui]\nagent_panel_sort = "spaces"\n'
    result = result.rstrip() + "\n\n" + fragment.strip() + "\n"
    try:
        actual = tomllib.loads(result)
    except tomllib.TOMLDecodeError as error:
        raise ValueError("Cannot safely edit this TOML layout; use the manual installation steps.") from error
    if actual != expected:
        raise ValueError("Config contains an unsupported table form; no settings were written. Use manual installation.")
    return result


def ghostty_mapping(text):
    mapping = "font-codepoint-map = U+E1A0-U+E1A8=Herdr Sidebar Logos"
    if mapping in text.splitlines():
        return text
    return text.rstrip() + "\n\n# Herdr Sidebar provider icons\n" + mapping + "\n"
