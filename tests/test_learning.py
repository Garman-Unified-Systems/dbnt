"""Tests for DBNT learning system."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dbnt.learning import DecayEngine, DecayState, LearningStore, PatternDetector


class TestDecayState:
    """Test FSRS-6 decay calculations."""

    def test_fresh_rule_full_retrievability(self):
        state = DecayState()
        assert state.retrievability() == 1.0

    def test_retrievability_decays(self):
        state = DecayState(stability=1.0)
        state.last_review = datetime.now(timezone.utc) - timedelta(days=10)
        r = state.retrievability()
        assert 0.0 < r < 1.0

    def test_higher_stability_slower_decay(self):
        past = datetime.now(timezone.utc) - timedelta(days=5)

        low = DecayState(stability=1.0, last_review=past)
        high = DecayState(stability=10.0, last_review=past)

        assert high.retrievability() > low.retrievability()

    def test_boost_increases_stability(self):
        state = DecayState(stability=1.0)
        old_stability = state.stability
        state.boost()
        assert state.stability > old_stability
        assert state.applied_count == 1

    def test_forgot_decreases_stability(self):
        state = DecayState(stability=2.0)
        state.last_review = datetime.now(timezone.utc)
        state.review(1)  # Forgot
        assert state.stability < 2.0

    def test_serialization_roundtrip(self):
        state = DecayState(stability=3.5, difficulty=0.3, review_count=5, applied_count=2)
        state.last_review = datetime.now(timezone.utc)

        restored = DecayState.from_dict(state.to_dict())
        assert restored.stability == state.stability
        assert restored.difficulty == state.difficulty
        assert restored.applied_count == state.applied_count


class TestLearningStore:
    """Test SQLite learning storage."""

    def test_add_and_retrieve(self):
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        store.add("Always use UTC datetimes", domain="code")

        learnings = store.get_unpromoted(domain="code")
        assert len(learnings) == 1
        assert learnings[0]["text"] == "Always use UTC datetimes"
        store.close()

    def test_mark_promoted(self):
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        lid = store.add("Test learning")
        store.mark_promoted([lid], "rule_123")

        unpromoted = store.get_unpromoted()
        assert len(unpromoted) == 0
        store.close()

    def test_count_by_domain(self):
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        store.add("A", domain="code")
        store.add("B", domain="code")
        store.add("C", domain="ops")

        counts = store.count()
        assert counts["code"] == 2
        assert counts["ops"] == 1
        store.close()

    def test_session_dedup_same_session_returns_original_id(self):
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        text = "Never push directly to main"
        sid = "session-abc"
        id1 = store.add(text, session_id=sid)
        id2 = store.add(text, session_id=sid)
        assert id1 == id2  # deduped — same row returned
        assert len(store.get_unpromoted()) == 1
        store.close()

    def test_session_dedup_different_session_creates_new_row_when_disabled(self):
        # cross_session_dedup=False: same text in different sessions = two rows
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        text = "Never push directly to main"
        id1 = store.add(text, session_id="session-1", cross_session_dedup=False)
        id2 = store.add(text, session_id="session-2", cross_session_dedup=False)
        assert id1 != id2  # different sessions, dedup disabled — two rows
        assert len(store.get_unpromoted()) == 2
        store.close()

    def test_cross_session_dedup_returns_existing_id(self):
        # Default: same text extracted in two different sessions → single row
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        text = "Never push directly to main"
        id1 = store.add(text, session_id="session-1")
        id2 = store.add(text, session_id="session-2")
        assert id1 == id2  # deduped across sessions — same row returned
        assert len(store.get_unpromoted()) == 1
        store.close()

    def test_cross_session_dedup_different_text_creates_new_row(self):
        # Cross-session dedup only dedupes identical text; different text always inserts
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        id1 = store.add("Always use UTC datetimes", session_id="session-1")
        id2 = store.add("Never push directly to main", session_id="session-2")
        assert id1 != id2  # different text — two rows even with default dedup
        assert len(store.get_unpromoted()) == 2
        store.close()

    def test_session_dedup_different_text_same_session_creates_new_row(self):
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        sid = "session-abc"
        id1 = store.add("Always use UTC datetimes", session_id=sid)
        id2 = store.add("Never push directly to main", session_id=sid)
        assert id1 != id2  # different text — two rows
        assert len(store.get_unpromoted()) == 2
        store.close()

    def test_sessionless_cross_session_dedup_does_not_dedup(self):
        # When session_id=None, cross_session_dedup=True is a no-op: the same text
        # added twice without a session_id creates two rows. Without an owning session,
        # there is no meaningful "cross-session" identity to check against, so we insert
        # rather than silently suppressing the second call.
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        text = "Never push directly to main"
        id1 = store.add(text)  # session_id=None, cross_session_dedup=True (default)
        id2 = store.add(text)  # same args — should NOT dedup
        assert id1 != id2, "sessionless calls should not dedup even with cross_session_dedup=True"
        assert len(store.get_unpromoted()) == 2
        store.close()

    def test_decay_state_persistence(self):
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        state = DecayState(stability=5.0, difficulty=0.3)
        state.boost()

        store.save_decay_state("rule_abc", state)
        loaded = store.get_decay_state("rule_abc")

        assert loaded.stability == state.stability
        assert loaded.applied_count == 1
        store.close()


class TestPatternDetector:
    """Test pattern detection and grouping."""

    def test_groups_similar(self):
        detector = PatternDetector(similarity_threshold=0.6)
        learnings = [
            {"text": "Always use timezone-aware datetimes", "domain": "code"},
            {"text": "Always use timezone aware datetime objects", "domain": "code"},
            {"text": "Use timezone-aware datetimes everywhere", "domain": "code"},
            {"text": "Something completely different", "domain": "code"},
        ]
        groups = detector.detect(learnings)
        assert len(groups) == 1  # One group of 3 similar
        assert groups[0].count == 3

    def test_no_singletons(self):
        detector = PatternDetector()
        learnings = [
            {"text": "Unique learning A", "domain": "code"},
            {"text": "Completely different B", "domain": "code"},
        ]
        groups = detector.detect(learnings)
        assert len(groups) == 0  # Singletons filtered out

    def test_should_promote(self):
        detector = PatternDetector(similarity_threshold=0.5)
        learnings = [
            {"text": "Never push to main directly", "domain": "git"},
            {"text": "Don't push directly to main", "domain": "git"},
            {"text": "Never push to main branch", "domain": "git"},
        ]
        groups = detector.detect(learnings)
        assert len(groups) == 1
        assert groups[0].should_promote is True

    def test_empty_input(self):
        detector = PatternDetector()
        assert detector.detect([]) == []


class TestDecayEngine:
    """Test decay sweep engine."""

    def test_new_rule_healthy(self):
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        engine = DecayEngine(store)

        result = engine.check("new_rule")
        assert result["status"] == "healthy"
        store.close()

    def test_boost_maintains_health(self):
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        engine = DecayEngine(store)

        state = engine.boost("rule_1")
        assert state.applied_count == 1

        result = engine.check("rule_1")
        assert result["status"] == "healthy"
        store.close()

    def test_sweep_categorizes(self):
        store = LearningStore(db_path=Path(tempfile.mkdtemp()) / "test.db")
        engine = DecayEngine(store)

        result = engine.sweep(["rule_a", "rule_b"])
        assert "healthy" in result
        assert "review" in result
        assert "archive" in result
        store.close()
