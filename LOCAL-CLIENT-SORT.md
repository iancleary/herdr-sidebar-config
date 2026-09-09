# Single-client sort watcher (Linux/WSL)

Both layout presets now use the same repo / branch / agent block. The refresh
hook reads the single `local-*.json` preference file under
`$XDG_STATE_HOME/herdr/client-shell` (default `~/.local/state/herdr/client-shell`).

- `spaces`: suppress duplicate headings within contiguous family/branch groups.
- `priority`: mirror Herdr's stable status-descending, state_change_seq-descending
  order, then suppress headings only within contiguous family/branch runs.
  A space heading repeats when another family intervenes. Native agent order
  breaks ties. Missing sequence data falls back to fully repeated context.
- Missing, malformed, unknown, or ambiguous client preferences: assume priority.
  This cannot establish the real client mode; use only with the documented
  single-client preference file present. No preferences are modified.

The supplied systemd user path unit watches the directory, including atomic
preference replacement. Its oneshot service invokes the existing plugin refresh
action. There is no polling loop or config rewrite. A mode toggle can briefly
display the old tokens until the asynchronous refresh completes.

Install these local units into `~/.config/systemd/user/`, then run:

```sh
systemctl --user daemon-reload
systemctl --user enable --now herdr-sidebar-sort.path
systemctl --user start herdr-sidebar-sort.service
```

The supplied units target the default Linux state directory and the Nix-profile
Herdr executable. Adapt those paths if XDG_STATE_HOME or the binary location
differs. This is a local opt-in installation, not part of setup_sidebar.py.
Disable before uninstalling the plugin:

```sh
systemctl --user disable --now herdr-sidebar-sort.path
```

This relies on an internal Herdr preference format and one local client/endpoint.
Multiple clients may overwrite the same preference. It does not alter Herdr's
sort algorithm or provide priority sorting of whole space groups.

Verification: unit tests cover atomic preference replacement, malformed and
ambiguous state, reordered agent blocks, and shared layout presets. A live
directory-event smoke test verifies service activation without changing the
user's saved sort preference. Visual toggling in Alacritty still needs the user.
