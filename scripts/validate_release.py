#!/usr/bin/env python3
"""Validate DBNT version consistency and an optional release tag."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SEMVER_TAG = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def project_version(pyproject_path: Path) -> str:
    """Read the project version without adding a TOML dependency on Python 3.10."""
    project_section = pyproject_path.read_text().split("[project]", 1)[1].split("\n[", 1)[0]
    match = re.search(r'^version\s*=\s*"([^"]+)"\s*$', project_section, re.MULTILINE)
    if match is None:
        raise ValueError(f"no [project] version found in {pyproject_path}")
    return match.group(1)


def runtime_version(init_path: Path) -> str:
    """Read ``dbnt.__version__`` without importing an unbuilt source tree."""
    match = re.search(r'^__version__\s*=\s*"([^"]+)"\s*$', init_path.read_text(), re.MULTILINE)
    if match is None:
        raise ValueError(f"no __version__ found in {init_path}")
    return match.group(1)


def plugin_version(manifest_path: Path) -> str:
    """Read the source-plugin version included in repository releases."""
    manifest = json.loads(manifest_path.read_text())
    version = manifest.get("version")
    if not isinstance(version, str):
        raise ValueError(f"no string version found in {manifest_path}")
    return version


def validate_release_tag(tag: str, version: str) -> None:
    """Require an exact stable ``vX.Y.Z`` tag matching the package version."""
    if SEMVER_TAG.fullmatch(tag) is None:
        raise ValueError(f"release tag must exactly match vX.Y.Z; got {tag!r}")
    if tag != f"v{version}":
        raise ValueError(f"release tag {tag!r} does not match package version {version!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="release tag to validate (for example v0.6.0)")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    metadata_version = project_version(root / "pyproject.toml")
    source_version = runtime_version(root / "src" / "dbnt" / "__init__.py")
    source_plugin_version = plugin_version(root / ".claude-plugin" / "plugin.json")
    if len({metadata_version, source_version, source_plugin_version}) != 1:
        raise ValueError(
            "version mismatch: "
            f"pyproject={metadata_version!r}, dbnt={source_version!r}, "
            f"plugin={source_plugin_version!r}"
        )
    if args.tag:
        validate_release_tag(args.tag, metadata_version)

    print(f"release contract valid for dbnt {metadata_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
