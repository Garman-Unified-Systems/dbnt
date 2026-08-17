"""Tests for the shared DBNT state-root contract."""

from pathlib import Path

from dbnt.adapters.claude_code import ClaudeCodeAdapter
from dbnt.adapters.generic import GenericAdapter
from dbnt.core import RuleStore, get_store
from dbnt.learning import LearningStore
from dbnt.protocol import Protocol
from dbnt.state import resolve_state_root


def test_state_root_defaults_to_home(monkeypatch, tmp_path):
    monkeypatch.delenv("DBNT_DIR", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

    assert resolve_state_root() == tmp_path / ".dbnt"


def test_state_root_honors_environment(monkeypatch, tmp_path):
    configured = tmp_path / "project-dbnt"
    monkeypatch.setenv("DBNT_DIR", str(configured))

    assert resolve_state_root() == configured
    assert RuleStore().base_path == configured / "rules"
    assert LearningStore().db_path == configured / "learnings.db"
    assert Protocol().state_dir == configured
    assert GenericAdapter().base_path == configured


def test_explicit_paths_override_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("DBNT_DIR", str(tmp_path / "environment"))
    explicit = tmp_path / "explicit"

    assert resolve_state_root(explicit) == explicit
    assert RuleStore(explicit / "rules").base_path == explicit / "rules"
    assert LearningStore(explicit / "learning.sqlite").db_path == explicit / "learning.sqlite"
    assert Protocol(explicit).state_dir == explicit
    assert GenericAdapter(explicit).base_path == explicit


def test_global_rule_store_follows_environment_changes(monkeypatch, tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"

    monkeypatch.setenv("DBNT_DIR", str(first))
    first_store = get_store()
    monkeypatch.setenv("DBNT_DIR", str(second))
    second_store = get_store()

    assert first_store.base_path == first / "rules"
    assert second_store.base_path == second / "rules"
    assert second_store is not first_store


def test_claude_adapter_resolves_state_without_moving_host_rule_mirror(monkeypatch, tmp_path):
    state_root = tmp_path / "state"
    claude_root = tmp_path / "claude"
    monkeypatch.setenv("DBNT_DIR", str(state_root))

    adapter = ClaudeCodeAdapter(claude_dir=claude_root)

    assert adapter.hooks_dir == claude_root / "hooks"
    assert adapter.state_dir == state_root
    assert adapter.rules_dir == claude_root / "rules"


def test_generated_hooks_honor_dbnt_dir(tmp_path):
    adapter = ClaudeCodeAdapter(claude_dir=tmp_path / "claude")
    adapter.hooks_dir.mkdir(parents=True)

    adapter._install_protocol_hook()
    adapter._install_learning_hook()

    protocol_hook = (adapter.hooks_dir / "dbnt-protocol.sh").read_text()
    learning_hook = (adapter.hooks_dir / "dbnt-learn.sh").read_text()
    assert 'SCORE_DIR="${DBNT_DIR:-$HOME/.dbnt}"' in protocol_hook
    assert "LearningStore()" in learning_hook
