# Local Spaces-style agent layout

The grouped Agents panel shows the repo/space name once per contiguous family,
then a `╰─ branch` heading once per contiguous branch group. Each agent row
displays its provider logo, a middle dot, a status circle, and its native tab
label/title. Priority mode mirrors native status/recency order before grouping
adjacent agents; headings repeat only when a different family/branch intervenes.
Task summaries remain available as compatibility tokens.
The only displayed connector is the thin curved branch elbow.

Heading-less agent rows receive two U+2800 blank cells to compensate Herdr's
first-row indent of 1 versus 3 cells on subsequent rows. Agents beneath branch
headings receive another two cells, including the first agent. Branch headings
without a repo heading also compensate the first-row offset. This local
workaround requires the Complete font's U+2800-to-space
mapping; portable padding needs an upstream renderer option. Herdr owns
selection styling and row offsets. A workspace heading identical to its
family name is not repeated.

Family identity uses native workspace.worktree.repo_key; names use repo_name.
Without provenance, each workspace is its own family. Branch labels use an
explicit workspace.branch if supplied, otherwise `git symbolic-ref --short HEAD`
in the reported checkout_path, once per checkout per refresh with a two-second
timeout. Missing/unavailable/detached branches omit the secondary row. As in
Spaces, the display removes a leading `worktree/` from actual branch names.
No branch name is inferred from a path. Linked-worktree indentation uses
workspace.worktree.is_linked_worktree.

The grouped layout renders ihs_repo and ihs_row_branch headings, then
ihs_row_logo, ihs_status, and ihs_row_tab. The old ihs_branch token remains for compatibility
but no longer creates a separate heading in this layout.
Both sort presets use the same layout; see LOCAL-CLIENT-SORT.md for the
single-client preference watcher. Shell-only panes do not create rows. A family
heading repeats if that family returns after another family in native pane order.

All source edits are local to this branch. Visual alignment must be checked in
the actual terminal; snapshot tokens alone cannot prove pixel alignment.
