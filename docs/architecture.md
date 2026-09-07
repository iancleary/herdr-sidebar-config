# How it works

Herdr owns agent detection, lifecycle state, sidebar rendering, and navigation.
This plugin turns those existing facts into display tokens. The layout file
decides how Herdr draws them; the bundled font supplies provider marks.

```text
Herdr lifecycle event
  -> run.sh -> sidebar.py
  -> herdr api snapshot
  -> workspace/tab grouping and task-title selection
  -> compare desired tokens with current tokens
  -> herdr pane report-metadata (changed panes only)
  -> Herdr renders sidebar-layout.toml
```

Each hook is a short Python process. A file lock serializes overlapping hooks.
No persistent worker, animation timer, or polling loop runs. A refresh reads one
snapshot and sends at most one metadata command per changed pane. The CLI calls
have timeouts. Frequent lifecycle events can still start many hooks; this is not
a claim of zero overhead or a measured benchmark.

In Herdr 0.9 multi-machine views, this flow runs independently on every server
that hosts panes. Each server publishes tokens into its own snapshot. The Herdr
client combines those endpoint snapshots and renders them with the viewing
client's sidebar and terminal configuration. Plugin registration and runtime
files do not propagate between machines.

## Grouping and titles

Snapshot order follows Herdr's workspace/tab/pane order. The layout requires
workspace sorting (`agent_panel_sort = "spaces"`) to keep headers beside their
agents. A workspace header lives on its first agent; a tab header lives on its
first agent within a workspace with more than one actual tab. Shell-only tabs
count toward tab identity but produce no agent rows.

The outer workspace-to-tab connection has no branch. Under each tab, agents use
`├─` and `└─`. A workspace with one tab has neither tab headings nor branches.
The tree is presentational, with native Herdr row selection and navigation.

Titles prefer a user `ihs_title` token. For a working Codex or Claude pane with a
native session ID, the plugin scans at most the final 512 KiB of that provider's
local history and selects its latest meaningful user instruction. Malformed
records, injected instruction headers, screenshot markers, and vague follow-ups
are skipped. Other cases use the existing terminal title, then tab, pane, and
provider fallbacks. These are deterministic local heuristics, not conversation
analysis or a model call.

## Token contract

Publisher: `plugin:iancleary.herdr-sidebar`.

| Token | Meaning |
| --- | --- |
| `ihs_group` | Workspace heading on its first agent |
| `ihs_tab` | Tab heading on its first agent, when multiple tabs exist |
| `ihs_logo` | Indentation, optional branch, and provider icon/text |
| `ihs_working`, `ihs_blocked`, `ihs_done`, `ihs_idle`, `ihs_unknown` | Exactly one populated with the native status symbol and task label |
| `ihs_gap` | Blank row after the last agent before another workspace |
| `ihs_title` | Optional user-owned title override; read but never written or cleared by this plugin |

Absent generated values are cleared, including when a pane stops being an
agent. Native identity/state and other plugins' metadata are not overwritten.
`clear` removes generated values from the current session. Run it before
disabling the plugin; future lifecycle events can repopulate them while enabled.

U+2800, a blank braille cell, preserves indentation through metadata whitespace
trimming. It is a spacer, not a loader. Herdr's first and continuation rows have
different native offsets, so the prefix arithmetic is intentional.

## Icon configuration

Set `icons` in the plugin config directory's `config.toml`:

| Value | Behavior |
| --- | --- |
| `"font"` | Use the bundled U+E1A0–U+E1A8 marks; setup's Ghostty default |
| `"text"` | Use short labels; selected by setup's `--text` |
| `"auto"` | Default without setup: use font mode if `fc-match` finds the exact family, otherwise text |

Font discovery does not prove the terminal has loaded the font. macOS without
Fontconfig will use text in auto mode; setup selects explicit font mode. The
Claude and Codex outlines extend beyond one nominal cell and use the following
space in Ghostty, which makes their size readable without shrinking the text.

## Development

Run `.venv/bin/python -m unittest discover -s tests -v` for dependency-free checks. Font
tests skip when the optional build dependency is unavailable. For all checks:

```sh
python3 -m venv .venv-font
.venv-font/bin/pip install -r requirements-font.txt
.venv-font/bin/python -m unittest discover -s tests -v
```

Rebuild fonts with `.venv-font/bin/python tools/build_font.py`, then
`.venv-font/bin/python tools/build_sidebar_font.py`. Commit the source changes
and matching `dist/` files. Tests compare rebuilt fonts byte for byte. Preserve
the artwork provenance in [third-party notices](../assets/THIRD_PARTY_NOTICES.md).

Live rendering verification uses Herdr 0.8.2 and Ghostty 1.3.1 on Linux. The
README capture comes from an isolated session with four demonstration agent
reports. Installation, repeat installation, doctor, font rendering, and
restoration of the original files were exercised there. The released Herdr
0.9.0 macOS binary also accepts the layout, manifest, actions, and event
subscriptions; its session snapshot retains the fields used by the plugin, and
an isolated `refresh` action exits successfully. Unit tests cover
single/multiple-tab transitions, unchanged metadata, unrelated settings, and
refusal to overwrite later edits. macOS terminal rendering and a live
multi-machine sidebar remain unverified.
