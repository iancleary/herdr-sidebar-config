#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"

uv sync --frozen
.venv/bin/python -m unittest discover -s tests -v
uv run --no-project --python 3.12 --with-requirements requirements-font.txt \
  python -m unittest discover -s tests -v
.venv/bin/python scripts/release_policy.py current >/dev/null
git diff --exit-code -- dist/
git diff --check
