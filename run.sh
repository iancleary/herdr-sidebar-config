#!/bin/sh
# Herdr hooks use a minimal PATH; include common Python installation locations.
export PATH="${HOME}/.local/bin:${HOME}/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${PATH:-}"
cd "$(dirname "$0")" || exit 1
exec python3 sidebar.py "$@"
