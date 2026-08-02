"""Tests for Claude Code adapter hook generation."""

import pytest

from dbnt.adapters.claude_code import ClaudeCodeAdapter
from dbnt.agency import ActionProposal, ActionRejectedError, Boundary, Effect


def test_protocol_hook_quarantines_corrupt_score(tmp_path):
    adapter = ClaudeCodeAdapter(claude_dir=tmp_path)
    adapter.hooks_dir.mkdir(parents=True)

    adapter._install_protocol_hook()

    hook = (tmp_path / "hooks" / "dbnt-protocol.sh").read_text()
    assert "${SCORE_FILE}.corrupt" in hook
    assert "initialize_score_file" in hook
    assert "validate_score_file" in hook
    assert '(.total_points // 0) | type == "number"' in hook
    assert '(.tweak_count // 0) | type == "number"' in hook
    assert 'all(.[]; type == "object"' in hook
    assert 'TMP_SCORE="${SCORE_FILE}.$$.tmp"' in hook


def test_adapter_run_action_enforces_policy_before_callback(tmp_path):
    adapter = ClaudeCodeAdapter(claude_dir=tmp_path)
    executed = False

    def external_mutation() -> None:
        nonlocal executed
        executed = True

    proposal = ActionProposal(
        name="merge",
        advances_outcome=True,
        effect=Effect.EXTERNAL_MUTATION,
        authorized_boundaries=frozenset({Boundary.EXTERNAL}),
    )

    with pytest.raises(ActionRejectedError):
        adapter.run_action(proposal, external_mutation)

    assert not executed


def test_adapter_run_action_executes_verified_move(tmp_path):
    adapter = ClaudeCodeAdapter(claude_dir=tmp_path)
    proposal = ActionProposal(
        name="apply local tested fix",
        advances_outcome=True,
        effect=Effect.LOCAL_MUTATION,
    )

    result = adapter.run_action(proposal, lambda: "done")

    assert result == "done"
