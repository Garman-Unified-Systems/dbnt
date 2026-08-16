"""Test that gate.sh exposes only the generic public project taxonomy."""

from pathlib import Path

GATE_SH = Path(__file__).parent.parent / "gate.sh"

GENERIC_PROJECT_TAXONOMY = (
    "proj-core",
    "proj-practice",
    "proj-tools",
    "proj-research",
    "proj-web",
    "proj-data",
    "proj-media",
    "proj-reference",
    "proj-infra",
    "proj-archive",
)

PROJECT_RULE_PREFIX = 'require_one_of "$project" "'


def _project_taxonomy_from_gate() -> tuple[str, ...]:
    rules = [
        line.strip()
        for line in GATE_SH.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith(PROJECT_RULE_PREFIX)
    ]
    assert len(rules) == 1, "gate.sh must define exactly one project taxonomy rule"

    rule = rules[0]
    assert rule.endswith('"'), "project taxonomy rule must end with a quoted allowlist"
    return tuple(rule[len(PROJECT_RULE_PREFIX) : -1].split())


def test_gate_taxonomy_matches_generic_public_contract():
    """The public gate must expose exactly the generic project allowlist."""
    assert _project_taxonomy_from_gate() == GENERIC_PROJECT_TAXONOMY
