#!/usr/bin/env python3
"""Validate this repository's SemVer release policy."""
from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def fail(message: str) -> None:
    raise SystemExit(message)


def load_toml(path: Path) -> dict:
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as error:
        fail(f"failed to read {path.relative_to(ROOT)}: {error}")


def current_version() -> str:
    pyproject = load_toml(ROOT / "pyproject.toml")
    plugin = load_toml(ROOT / "herdr-plugin.toml")
    lock = load_toml(ROOT / "uv.lock")
    try:
        lock_package = next(
            package for package in lock["package"]
            if package["name"] == "herdr-sidebar-config"
        )
        versions = {
            "pyproject.toml": pyproject["project"]["version"],
            "herdr-plugin.toml": plugin["version"],
            "uv.lock": lock_package["version"],
        }
    except (KeyError, StopIteration, TypeError) as error:
        fail(f"failed to locate every release version: {error}")
    if not all(isinstance(value, str) for value in versions.values()):
        fail("release versions must be strings")
    if len(set(versions.values())) != 1:
        details = ", ".join(f"{path}={version}" for path, version in versions.items())
        fail(f"release versions do not match: {details}")
    version = next(iter(versions.values()))
    if not SEMVER.fullmatch(version):
        fail(f"release version is not SemVer: {version}")
    return version


def tag_exists(tag: str) -> bool:
    local = subprocess.run(
        ["git", "tag", "--list", tag], cwd=ROOT,
        check=False, capture_output=True, text=True,
    )
    if local.returncode:
        fail(local.stderr.strip() or "failed to inspect local tags")
    if local.stdout.strip():
        return True
    remote = subprocess.run(
        ["git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"],
        cwd=ROOT, check=False, capture_output=True, text=True,
    )
    if remote.returncode:
        fail(remote.stderr.strip() or "failed to inspect origin tags")
    return bool(remote.stdout.strip())


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"current", "next", "validate"}:
        fail("usage: release_policy.py current|next|validate [VERSION]")
    command = sys.argv[1]
    version = current_version()
    if command == "current":
        if len(sys.argv) != 2:
            fail("current does not accept a version")
        print(version)
        return 0
    if command == "validate":
        if len(sys.argv) != 3:
            fail("validate requires VERSION")
        requested = sys.argv[2]
        if not SEMVER.fullmatch(requested):
            fail(f"requested version is not SemVer: {requested}")
        if requested != version:
            fail(
                f"requested version {requested} does not match the committed "
                f"manifest version {version}"
            )
        return 0
    if len(sys.argv) != 2:
        fail("next does not accept a version")
    tag = f"v{version}"
    if tag_exists(tag):
        fail(
            f"{tag} already exists; update pyproject.toml and herdr-plugin.toml, "
            "then refresh uv.lock before planning another release"
        )
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
