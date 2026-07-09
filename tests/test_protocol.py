"""Tests for DBNT protocol."""

import json
import tempfile
from pathlib import Path

import pytest

from dbnt.protocol import Action, Command, Protocol


class TestCommandDetection:
    """Test command detection from text."""

    def test_db(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("db")
        assert r.command == Command.DB
        assert r.action == Action.ENCODE_SUCCESS

    def test_db_with_context(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("db that's wrong")
        assert r.command == Command.DB

    def test_dbn(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("dbn")
        assert r.command == Command.DBN

    def test_dbnm(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("dbnm")
        assert r.command == Command.DBNM
        assert r.action == Action.ENCODE_SUCCESS

    def test_dbyc(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("dbyc")
        assert r.command == Command.DBYC
        assert r.action == Action.ENCODE_BOTH
        assert r.points == -2.0

    def test_fixed(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("fixed")
        assert r.command == Command.GOOD
        assert r.points > 0

    def test_ship_it(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("ship it")
        assert r.command == Command.GOOD

    def test_tweak(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("tweak")
        assert r.command == Command.TWEAK
        assert r.action == Action.ITERATE

    def test_no_command(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("please refactor the auth module")
        assert r.command == Command.NONE
        assert r.action == Action.NONE

    def test_dbn_does_not_match_dbnm(self):
        """DBN should not trigger on DBNM."""
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("dbnm")
        assert r.command == Command.DBNM

    def test_db_does_not_match_dbn(self):
        """DB should not trigger on DBN."""
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("dbn")
        assert r.command == Command.DBN

    # ─── False positive prevention ─────────────────────────────────────

    def test_db_not_triggered_by_database(self):
        """'the db connection' should NOT trigger DB command."""
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("check the db connection")
        assert r.command == Command.NONE

    def test_good_not_triggered_in_sentence(self):
        """'good approach' should NOT trigger GOOD command."""
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("that's a good approach")
        assert r.command == Command.NONE

    def test_close_not_triggered_by_close_pr(self):
        """'close the PR' should NOT trigger TWEAK."""
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("close the PR")
        assert r.command == Command.NONE

    def test_almost_not_triggered(self):
        """'almost' should NOT trigger TWEAK (removed from patterns)."""
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("almost done")
        assert r.command == Command.NONE


class TestScoring:
    """Test scoring system."""

    def test_score_persists(self):
        d = Path(tempfile.mkdtemp())
        p = Protocol(state_dir=d)
        p.process("db")
        p.process("fixed")

        # Reload from disk
        p2 = Protocol(state_dir=d)
        assert p2.state.total_points != 0
        assert len(p2.state.events) == 2

    def test_tweak_degradation(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r1 = p.process("tweak")
        assert r1.points == 0.5  # First tweak
        r2 = p.process("tweak")
        assert r2.points < 0  # Subsequent tweaks degrade

    def test_good_resets_tweak_count(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        p.process("tweak")
        p.process("tweak")
        p.process("fixed")
        assert p.state.tweak_count == 0

    def test_success_weighted(self):
        """Fixed should be weighted 1.5x."""
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("fixed")
        assert r.points == 3.0  # 2.0 * 1.5

    def test_corrupt_score_is_quarantined_and_rebuilt(self, tmp_path):
        score_path = tmp_path / "score.json"
        score_path.write_text('{"total_points": 7, "events": []}\n"}\n')

        p = Protocol(state_dir=tmp_path)
        assert p.state.total_points == 0

        quarantined = [
            path for path in tmp_path.glob("score.json.corrupt-*")
            if not path.name.endswith(".reason")
        ]
        assert len(quarantined) == 1
        assert '"total_points": 7' in quarantined[0].read_text()
        assert list(tmp_path.glob("score.json.corrupt-*.reason"))

        p.process("fixed")

        p2 = Protocol(state_dir=tmp_path)
        assert p2.state.total_points == 3.0
        assert len(p2.state.events) == 1
        assert not list(tmp_path.glob("score.json.*.tmp"))

    @pytest.mark.parametrize(
        "payload",
        [
            [],
            {"events": [7]},
            {"events": "wrong-type"},
            {"total_points": "7", "events": []},
            {"total_points": True, "events": []},
            {"events": [], "tweak_count": 1.5},
            {"events": [], "tweak_count": -1},
            {"events": [{"points": "3"}]},
        ],
    )
    def test_wrong_shape_score_is_quarantined_and_returns_clean_state(
        self, tmp_path, payload
    ):
        score_path = tmp_path / "score.json"
        score_path.write_text(json.dumps(payload))

        state = Protocol(state_dir=tmp_path).state

        assert state.total_points == 0.0
        assert state.events == []
        assert state.tweak_count == 0
        quarantined = [
            path
            for path in tmp_path.glob("score.json.corrupt-*")
            if not path.name.endswith(".reason")
        ]
        assert len(quarantined) == 1
        assert list(tmp_path.glob("score.json.corrupt-*.reason"))


class TestResponseText:
    """Test response text."""

    def test_yes_chef(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("db")
        assert "Yes Chef" in r.response_text

    def test_dbyc_encodes_both(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("dbyc")
        assert "both" in r.response_text.lower() or "failure" in r.response_text.lower()

    def test_good_response_shows_correct_points(self):
        p = Protocol(state_dir=Path(tempfile.mkdtemp()))
        r = p.process("fixed")
        assert "+3" in r.response_text
