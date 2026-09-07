#!/bin/sh
# Herdr hooks use a minimal PATH. The project environment is created by
# `uv sync`; using it directly keeps refresh hooks off macOS's system Python.
root="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)" || exit 1
python="$root/.venv/bin/python"

if [ ! -x "$python" ]; then
  echo "Herdr Sidebar: missing $python; run 'uv sync' in $root." >&2
  exit 1
fi

cd "$root" || exit 1
exec "$python" sidebar.py "$@"
