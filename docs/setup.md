# Setup and troubleshooting

Use the [README quick start](../README.md#install) for the supported installation
flow. Run `uv sync` in the checkout first. Run setup from the same checkout and
Herdr session each time.

## Files setup manages

| Item | Default location |
| --- | --- |
| Herdr layout | `$XDG_CONFIG_HOME/herdr/config.toml`, or `~/.config/herdr/config.toml` |
| Plugin icon setting | The directory printed by `herdr plugin config-dir iancleary.herdr-sidebar`, then `config.toml` |
| Linux font | `~/.local/share/fonts/HerdrSidebarLogos-Regular.ttf` |
| macOS font | `~/Library/Fonts/HerdrSidebarLogos-Regular.ttf` |
| Linux Ghostty config | `$XDG_CONFIG_HOME/ghostty/config`, or `~/.config/ghostty/config` |
| macOS Ghostty config | `~/Library/Application Support/com.mitchellh.ghostty/config` |
| Backups | `iancleary-herdr-sidebar-setup/install.json` beside the Herdr config |

`HERDR_CONFIG_PATH` selects a non-default Herdr config. It must be the config of
the running session. `--config` may name that same path, but cannot retarget an
already-running server. `--ghostty-config`, `--font-dir`, and `--state-dir` accept
explicit paths; repeat custom path flags for doctor and uninstall.

The installer edits `[ui.sidebar.agents]` and its child tables, and sets
`[ui].agent_panel_sort = "spaces"`. Other parsed settings must remain equal or
setup refuses the edit. Ordinary tables and array tables are supported; unusual
inline/dotted table forms may require manual installation. A matching existing
layout is left alone.

Backups contain original file bytes, including any private values already in
your config. They are local files written with restrictive permissions; never
publish them. Repeated installs retain the first backup. Setup and removal stop
if a tracked file has since changed. An interrupted setup retains its backup for
inspection and recovery. The helper is intended for one active session at a
time; other running sessions that share the config may need their own refresh.

## Managed-configuration integration

Use this path when Home Manager, chezmoi, a dotfiles repository, or another
configuration manager owns the Herdr or terminal configuration. Do not edit a
generated file or symlink. Do not run the automatic installer against it. The
installer resolves configured paths before it writes backups and changes, so a
managed link can resolve to a read-only store or another generated target.

Integrate every item in this table. The plugin needs all applicable items; a
terminal font mapping alone does not install the plugin or its font.

| Item | Required integration |
| --- | --- |
| Checkout | Keep this repository at a stable path and run `uv sync` there. The plugin hook uses `.venv/bin/python` from this checkout. |
| Plugin registration | From the checkout, run `herdr plugin link "$PWD" --disabled`. |
| Herdr configuration | Merge `sidebar-layout.toml` into the manager's source for the active Herdr config. Set `agent_panel_sort = "spaces"` in its existing `[ui]` table. Apply the manager before reloading Herdr. |
| Plugin setting | In the directory printed by `herdr plugin config-dir iancleary.herdr-sidebar`, create `config.toml` with either `icons = "font"` or `icons = "text"`. Manage this file too if the setup owns all persistent configuration. |
| Icon font | In font mode, install `dist/HerdrSidebarLogos-Regular.ttf` in the platform font directory listed above. The configuration manager can own this copy. |
| Terminal mapping | In font mode, add the `font-codepoint-map` line below to the terminal configuration source. Do not add a duplicate if an effective configuration already supplies it. |
| Activation | Check and reload the applied Herdr config. Enable the plugin and invoke its `refresh` action. |
| Verification | Run doctor with the effective managed paths, then inspect the rendered sidebar. Start a fresh Ghostty process after a new font installation. |

For example, if the effective Ghostty settings live in a secondary managed
file, pass that file to doctor:

```sh
.venv/bin/python setup_sidebar.py doctor \
  --ghostty-config "$HOME/path/to/effective-ghostty-config"
```

Doctor reads managed files safely. It does not prove that the configuration
manager applied the intended source or that a running terminal loaded a newly
installed font. Verify both separately.

## Herdr 0.9 multi-machine setup

Herdr 0.9 can show local and saved SSH machines in one client. Plugin
registration is local to each Herdr installation; it is not copied to other
machines. Presentation settings are local to the client that renders the
sidebar. Split the installation by responsibility:

| Location | Install or configure |
| --- | --- |
| Every machine that hosts agent panes | A stable plugin checkout, `uv sync`, the plugin link, the plugin `config.toml`, and plugin enablement. |
| Every computer that displays a Herdr client | The Herdr sidebar layout and workspace sorting. In font mode, also install the font and configure the terminal mapping. |

A computer that both hosts panes and displays Herdr needs both sets. A remote
agent host does not need the icon font merely to publish font-mode tokens. The
viewing computer needs the font because it renders those private-use
codepoints.

Set `icons = "font"` or `icons = "text"` explicitly on each agent host. Do not
depend on `icons = "auto"` for remote viewing: automatic detection checks for
the font on the machine where the plugin runs, not on the viewing client.

After installation, invoke `refresh` and inspect the plugin log on each agent
host. Then inspect the combined sidebar from each viewing client. A successful
local plugin log does not verify installation on another machine.

## Manual installation

Use these commands to complete a managed integration or to preserve a
customized sidebar. In a managed setup, each reference to a configuration file
means its source of truth, followed by the manager's normal apply command.

1. Clone the repository, keep that checkout, and run `uv sync`. Back up each
   directly edited file. Do not back up generated managed links as if they were
   source files.
2. Run `herdr plugin link "$PWD" --disabled` from the repository root.
3. Merge [sidebar-layout.toml](../sidebar-layout.toml) into your Herdr config,
   replacing existing `[ui.sidebar.agents]` tables. Set
   `agent_panel_sort = "spaces"` in the existing `[ui]` table. Do not create a
   duplicate `[ui]` table. Apply the configuration manager now, if present.
4. Run `herdr plugin config-dir iancleary.herdr-sidebar`. In that directory's
   `config.toml`, set `icons = "text"` for portable labels, or `icons = "font"`
   after completing the font steps below.
5. Run `herdr config check`, then `herdr server reload-config`.
6. Run `herdr plugin enable iancleary.herdr-sidebar`, then
   `herdr plugin action invoke refresh --plugin iancleary.herdr-sidebar`.

For font mode, copy `dist/HerdrSidebarLogos-Regular.ttf` to your platform's font
directory in the table above, or declare that file in the configuration manager.
On Linux, run `fc-cache -f` afterward. Add this to the effective Ghostty config,
then apply the configuration and open a fresh Ghostty process:

```ini
font-codepoint-map = U+E1A0-U+E1A8=Herdr Sidebar Logos
```

The font uses nine private-use codepoints. Only that range is remapped; your
regular terminal font remains in use for text. If another mapping overlaps the
range, resolve it explicitly. Other terminals need their own font fallback or
codepoint mapping configuration; use text mode if unsure.

## Manual removal

Use this if setup has no backup or refuses to replace a file edited later.

1. Run `herdr plugin action invoke clear --plugin iancleary.herdr-sidebar` while
   the plugin is enabled, then `herdr plugin disable iancleary.herdr-sidebar`.
2. Restore only the old `[ui.sidebar.agents]` tables and `agent_panel_sort` from
   your backup, preserving newer unrelated settings. If you had no custom
   sidebar before installation, remove those tables and the sort override to
   return to Herdr defaults.
3. Remove the Herdr Sidebar font mapping from Ghostty. Remove the font only if
   nothing else uses it. Refresh Linux's font cache with `fc-cache -f`.
4. Run `herdr config check` and `herdr server reload-config`.

The setup backup's `files` object maps absolute paths to `before` (base64 original
bytes, or null if the file did not exist) and `installed_sha256`. Decode selected
`before` values locally to inspect them; do not blindly restore an entire config
over subsequent edits. Retire the old backup after manual recovery before using
automatic setup again. A disabled local plugin registration is harmless and
keeps removal from deleting a user's checkout.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Setup says to run inside Herdr | Open a terminal pane in the intended session; do not spoof `HERDR_ENV` to target an unknown socket. |
| Icons are empty squares | Start a fresh Ghostty process. On Linux, `fc-match 'Herdr Sidebar Logos'` should name that family. Confirm the codepoint mapping above. |
| Icons appear too small or boxed | Confirm the family is **Herdr Sidebar Logos**, not the earlier Herdr Harness Logos font. The bundled Codex outline has no surrounding square. |
| Rows are blank | Run doctor, check the plugin is enabled, and invoke refresh. The custom layout needs the plugin's metadata. |
| A task label is stale | Focus the pane or invoke refresh. Titles update on lifecycle/focus events, not on each byte of terminal output. |
| Tabs look flat | A workspace with one tab deliberately hides tab headings. Add a second tab to see the tree. |
| Doctor reports a failed hook | Inspect `herdr plugin log list --plugin iancleary.herdr-sidebar --limit 5`. Confirm that `uv sync` created `.venv/bin/python`. |

Doctor checks plugin registration, layout, sorting, the latest hook result, and
font files/mapping in explicit font mode. It cannot inspect Ghostty's in-memory
font cache or prove that the user is looking at the same session.
