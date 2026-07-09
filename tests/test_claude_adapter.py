"""Tests for Claude Code adapter hook generation."""

from dbnt.adapters.claude_code import ClaudeCodeAdapter


def test_protocol_hook_quarantines_corrupt_score(tmp_path):
    adapter = ClaudeCodeAdapter(claude_dir=tmp_path)
    adapter.hooks_dir.mkdir(parents=True)

    adapter._install_protocol_hook()

    hook = (tmp_path / "hooks" / "dbnt-protocol.sh").read_text()
    assert "${SCORE_FILE}.corrupt" in hook
    assert "initialize_score_file" in hook
    assert "jq -e 'type == \"object\"" in hook
    assert 'TMP_SCORE="${SCORE_FILE}.$$.tmp"' in hook
