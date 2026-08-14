"""Test that gate.sh project taxonomy uses generic labels without internal project names."""
import pathlib
import re


GATE_SH = pathlib.Path(__file__).parent.parent / "gate.sh"

NEW_LABELS = [
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
]

REMOVED_INTERNAL_NAMES = [
    "proj-gus",
    "proj-office-369",
    "proj-abacus",
    "proj-borussia",
    "proj-splat",
    "proj-finance",
    "proj-straincellar",
    "proj-abledumb",
    "proj-familyrecipes",
    "proj-sites",
    "proj-research-kb",
    "proj-substrate",
]


def test_gate_taxonomy_uses_generic_labels():
    """All new generic taxonomy labels must appear in gate.sh."""
    content = GATE_SH.read_text()
    for label in NEW_LABELS:
        assert label in content, f"Expected generic label '{label}' in gate.sh"


def test_gate_taxonomy_removes_internal_names():
    """No internal project names may appear in gate.sh."""
    content = GATE_SH.read_text()
    for name in REMOVED_INTERNAL_NAMES:
        assert name not in content, f"Internal project name '{name}' must not appear in gate.sh (public repo)"
