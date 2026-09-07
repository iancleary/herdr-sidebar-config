# Release process

This repository uses Semantic Versioning with `v`-prefixed Git tags. A GitHub
release publishes the tested repository state. It does not publish a Python
package or a separate plugin archive.

## Version policy

The version must match in these files:

- `pyproject.toml`
- `herdr-plugin.toml`
- `uv.lock`

Use patch versions for compatible fixes and documentation. Use minor versions
for compatible plugin behavior or configuration features. Use a major version
for an incompatible plugin, configuration, or installation contract.

Prepare a version change in a normal pull request. Update both TOML manifests,
then run `uv lock` to refresh `uv.lock`. Do not make version changes during
public release execution. This keeps the tagged commit identical to the commit
that passed review and CI.

## Release contract

[`release.toml`](../release.toml) is repository policy. The unchanged shared
runner is vendored at [`scripts/release.py`](../scripts/release.py). Its source
commit and SHA-256 are pinned in `release.toml`. Repository-specific version
validation stays in [`scripts/release_policy.py`](../scripts/release_policy.py).

The runner requires:

- a clean `main` branch at the intended `origin/main` commit
- matching SemVer values in all three version files
- an absent local and remote `v<version>` tag
- the complete local check in `scripts/check.sh`
- working GitHub CLI authentication

The checked-in GitHub Actions workflow is the review gate. Confirm that it
succeeded for the intended commit before release execution. The release runner
runs the equivalent complete check locally; it does not dispatch another CI
workflow.

GitHub generates release notes by default. Pass `--notes-file <path>` when a
release needs curated notes.

## Verify and publish

Use `release-runner` for ordinary releases. Run the checked-in runner directly;
Forge is not required:

```sh
uv run scripts/release.py check --json
uv run scripts/release.py plan --json
```

Read `version`, `target_commit`, and `config_sha256` from the plan. Use those
exact values for dry-run and apply:

```sh
uv run scripts/release.py run --dry-run \
  --version <version> \
  --expected-head <target_commit> \
  --expected-config <config_sha256> \
  --json

uv run scripts/release.py run --apply \
  --version <version> \
  --expected-head <target_commit> \
  --expected-config <config_sha256> \
  --json
```

Run apply only when the user explicitly requests publication. Apply creates an
annotated tag, pushes it to `origin`, and creates the GitHub release. It does not
rewrite version files or create a release commit.

If GitHub release creation fails after the tag push, inspect the remote tag and
its commit. Use the runner's documented `--resume` path with the exact version
and tagged commit. Do not move or recreate a conflicting tag.

## Workflow maintenance

Use `create-release-process` to audit or change this workflow. Keep repository
policy in `release.toml` and small helpers. Keep `scripts/release.py` identical
to its pinned `iancleary/release-skills` source. To update it, inspect a released
upstream commit, copy the runner unchanged, update both provenance values, and
repeat check, plan, and dry-run verification.
