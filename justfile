set positional-arguments

python := ".venv/bin/python"

# Show the available repository tasks.
default:
    @just --list

# Create or update the pinned plugin environment.
setup:
    uv sync

# Preview installation changes. Pass --text or --sort priority when needed.
install-preview *args:
    {{python}} setup_sidebar.py install --dry-run --json {{args}}

# Install the plugin. Run install-preview first.
install *args:
    {{python}} setup_sidebar.py install --json {{args}}

# Check the installed configuration and plugin hook.
doctor:
    {{python}} setup_sidebar.py doctor --json

# Preview removal without changing files.
uninstall-preview:
    {{python}} setup_sidebar.py uninstall --dry-run --json

# Restore files backed up during installation.
uninstall:
    {{python}} setup_sidebar.py uninstall --json
