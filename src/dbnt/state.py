"""Resolve the one filesystem root used by all DBNT state."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_state_root(explicit: str | Path | None = None) -> Path:
    """Return the DBNT state root.

    An explicit constructor argument wins, followed by ``DBNT_DIR``, then the
    backwards-compatible ``~/.dbnt`` default. Relative paths intentionally stay
    relative to the caller's working directory so ``DBNT_DIR=./dbnt`` supports
    project-local stores.
    """
    if explicit is not None:
        return Path(explicit).expanduser()

    configured = os.environ.get("DBNT_DIR")
    if configured:
        return Path(configured).expanduser()

    return Path.home() / ".dbnt"
