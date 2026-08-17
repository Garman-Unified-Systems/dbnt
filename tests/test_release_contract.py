"""Tests that keep source, package metadata, and release tags aligned."""

import json
from pathlib import Path

import pytest
from scripts.validate_release import project_version, validate_release_tag

import dbnt

ROOT = Path(__file__).parents[1]


def test_project_and_runtime_versions_match():
    assert project_version(ROOT / "pyproject.toml") == dbnt.__version__


def test_plugin_manifest_version_and_homepage_match_release():
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())

    assert manifest["version"] == dbnt.__version__
    assert manifest["homepage"] == "https://github.com/Garman-Unified-Systems/dbnt"


@pytest.mark.parametrize("tag", ["v0.6.0", "v10.20.30"])
def test_release_tag_accepts_exact_semver_matching_package(tag):
    version = tag.removeprefix("v")
    validate_release_tag(tag, version)


@pytest.mark.parametrize(
    ("tag", "version"),
    [
        ("0.6.0", "0.6.0"),
        ("v0.6", "0.6.0"),
        ("v0.6.0-rc1", "0.6.0"),
        ("v0.6.1", "0.6.0"),
        ("main", "0.6.0"),
    ],
)
def test_release_tag_rejects_nonexact_or_mismatched_values(tag, version):
    with pytest.raises(ValueError):
        validate_release_tag(tag, version)


def test_publish_workflow_is_tag_only_and_validates_artifacts():
    workflow = (ROOT / ".github" / "workflows" / "publish.yml").read_text()

    assert "workflow_dispatch" not in workflow
    assert "scripts/validate_release.py" in workflow
    assert "fetch-depth: 0" in workflow
    assert "git merge-base --is-ancestor" in workflow
    assert "ruff check" in workflow
    assert "pytest" in workflow
    assert "twine check dist/*" in workflow


def test_repo_gate_builds_and_checks_distributions():
    gate = (ROOT / "gate.sh").read_text()

    assert "scripts/validate_release.py" in gate
    assert "-m build --outdir" in gate
    assert "-m twine check" in gate


def test_source_plugin_hooks_share_state_root_and_allow_schema():
    for name in ("dbnt-protocol.sh", "dbnt-learn.sh"):
        hook = (ROOT / "hooks" / name).read_text()
        assert "DBNT_DIR" in hook
        assert '{"continue":true}' in hook
        assert '{"result":"continue"}' not in hook
        assert "$HOME/DEV/dbnt" not in hook


def test_lifecycle_docs_require_explicit_promotion_and_report_only_checks():
    readme = (ROOT / "README.md").read_text()
    prd = (ROOT / "prd.md").read_text()

    for stale_claim in (
        "pattern-detected, auto-promoted",
        "Three occurrences of the same pattern auto-promotes it",
        "`dbnt dissonance` surfaces conflicting rules",
        "Similar corrections cluster automatically",
        "without manual rule-writing",
        "Frequently-applied rules gain stability",
    ):
        assert stale_claim not in readme
    assert "aggregate success/failure balance" in readme
    assert "only when an operator runs `dbnt promote`" in readme

    for stale_claim in (
        "keeping the rule store lean",
        "Pattern Detection + Auto-Promotion",
        "the pattern auto-promotes to a permanent rule",
        "3+ occurrences triggers promotion",
        "Boost on application (rating=3)",
    ):
        assert stale_claim not in prd
    assert "only when an operator runs `dbnt promote`" in prd
