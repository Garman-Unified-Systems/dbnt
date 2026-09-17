#!/usr/bin/env bash
# install-hooks.sh — configure git to use .githooks for this repo.
#
# Run once after cloning:
#   bash scripts/install-hooks.sh
#
# This sets core.hooksPath = .githooks so git runs the bundled hooks
# (pre-commit, pre-merge-commit, pre-push) for every local operation.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "ERROR: run this script from inside the dbnt repo." >&2
    exit 1
}

HOOKS_DIR="$REPO_ROOT/.githooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo "ERROR: .githooks directory not found at $HOOKS_DIR" >&2
    exit 1
fi

# Make all hook scripts executable.
chmod +x "$HOOKS_DIR"/*

git -C "$REPO_ROOT" config core.hooksPath .githooks

echo "Hooks installed. git will now run .githooks/{pre-commit,pre-merge-commit,pre-push}."
echo "Requires: pip install -e '.[dev]'  (lizard==1.24.0 must be present)"
