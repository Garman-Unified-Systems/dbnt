"""DBNT Learning System — detect patterns, decay unused rules, promote recurring ones."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

# ─── FSRS-6 Simplified Decay ───────────────────────────────────────────────

@dataclass
class DecayState:
    """FSRS-inspired decay state for a rule."""
    stability: float = 1.0     # Days until retrievability drops to 90%
    difficulty: float = 0.5    # 0.0 (easy) to 1.0 (hard)
    last_review: datetime | None = None
    review_count: int = 0
    applied_count: int = 0

    def retrievability(self, now: datetime | None = None) -> float:
        """Calculate current retrievability using FSRS-6 power formula.

        R(t, S) = (1 + t / (9 * S))^(-1)

        Where t = elapsed days, S = stability.
        Returns 0.0-1.0 (1.0 = perfectly remembered).
        """
        if self.last_review is None:
            return 1.0
        now = now or datetime.now(timezone.utc)
        elapsed_days = (now - self.last_review).total_seconds() / 86400
        if self.stability <= 0:
            return 0.0
        return (1 + elapsed_days / (9 * self.stability)) ** -1

    def review(self, rating: int) -> None:
        """Update state after a review/application.

        Rating scale:
            1 = forgot/failed (rule wasn't applied when it should have been)
            2 = hard (applied but with difficulty)
            3 = good (applied correctly)
            4 = easy (applied effortlessly)
        """
        rating = max(1, min(4, rating))
        self.review_count += 1
        self.last_review = datetime.now(timezone.utc)

        # Stability update (simplified FSRS-6)
        if rating == 1:  # Forgot
            self.stability *= 0.5
            self.difficulty = min(1.0, self.difficulty + 0.1)
        elif rating == 2:  # Hard
            self.stability *= 0.8
            self.difficulty = min(1.0, self.difficulty + 0.05)
        elif rating == 3:  # Good
            self.stability *= (1 + 0.5 * (1 - self.difficulty))
            self.difficulty = max(0.0, self.difficulty - 0.05)
        elif rating == 4:  # Easy
            self.stability *= (1 + 1.0 * (1 - self.difficulty))
            self.difficulty = max(0.0, self.difficulty - 0.1)

    def boost(self) -> None:
        """Boost when rule is successfully applied. Equivalent to rating=3."""
        self.applied_count += 1
        self.review(3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stability": round(self.stability, 3),
            "difficulty": round(self.difficulty, 3),
            "last_review": self.last_review.isoformat() if self.last_review else None,
            "review_count": self.review_count,
            "applied_count": self.applied_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecayState:
        state = cls(
            stability=data.get("stability", 1.0),
            difficulty=data.get("difficulty", 0.5),
            review_count=data.get("review_count", 0),
            applied_count=data.get("applied_count", 0),
        )
        lr = data.get("last_review")
        if lr:
            # Handle 'Z' suffix (Python 3.10 compat)
            if lr.endswith("Z"):
                lr = lr[:-1] + "+00:00"
            state.last_review = datetime.fromisoformat(lr)
        return state


# ─── Learning Store (SQLite) ───────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    source TEXT DEFAULT 'unknown',
    domain TEXT DEFAULT 'general',
    importance REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    session_id TEXT,
    promoted_to TEXT  -- rule ID if promoted
);

CREATE TABLE IF NOT EXISTS rule_decay (
    rule_id TEXT PRIMARY KEY,
    stability REAL DEFAULT 1.0,
    difficulty REAL DEFAULT 0.5,
    last_review TEXT,
    review_count INTEGER DEFAULT 0,
    applied_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_learnings_domain ON learnings(domain);
CREATE INDEX IF NOT EXISTS idx_learnings_promoted ON learnings(promoted_to);
CREATE INDEX IF NOT EXISTS idx_learnings_session_text ON learnings(session_id);
CREATE INDEX IF NOT EXISTS idx_learnings_dedup_key ON learnings(LOWER(SUBSTR(TRIM(text), 1, 80)));
"""


# Patterns that indicate system-prompt or tool-suggestion contamination.
# These strings appear in Claude's internal system reminders and shell command
# suggestions — never from real user feedback. Entries matching any pattern
# are silently dropped in LearningStore.add().
_CONTAMINATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^Use tool_use:", re.IGNORECASE),
    re.compile(r"^Use Bash to run", re.IGNORECASE),
    re.compile(r"respond to these messages or otherwise consider", re.IGNORECASE),
    re.compile(r"system.reminder", re.IGNORECASE),
    re.compile(r"<system-reminder>", re.IGNORECASE),
    re.compile(r"IMPORTANT:.*after completing", re.IGNORECASE),
    re.compile(r"task.notification", re.IGNORECASE),
]


def _is_contaminated(text: str) -> bool:
    """Return True if text looks like system-prompt or tool-suggestion noise."""
    return any(pattern.search(text) for pattern in _CONTAMINATION_PATTERNS)


class LearningStore:
    """SQLite-backed learning storage. Supports context manager protocol."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or Path.home() / ".dbnt" / "learnings.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def __enter__(self) -> LearningStore:
        return self

    def __exit__(self, *_args: object) -> None:  # pyright: ignore[reportUnusedParameter]
        self.close()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self) -> None:
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    def add(
        self,
        text: str,
        source: str = "unknown",
        domain: str = "general",
        importance: float = 1.0,
        session_id: str | None = None,
        cross_session_dedup: bool = True,
    ) -> int:
        """Add a learning. Returns the learning ID.

        Dedup logic (both checks use the first 80 normalized chars):
        1. Cross-session dedup (default ON): if identical text already exists in
           ANY session, return the existing ID without inserting. This prevents
           the same pattern being re-extracted in every new session and inflating
           the pattern detector's counts.
        2. Within-session dedup: if the same text appears twice in the same
           session, return the existing ID. Runs even when cross_session_dedup
           is False.

        Set cross_session_dedup=False to allow the same text to accumulate
        across sessions (e.g. for explicit frequency tracking).
        """
        if _is_contaminated(text):
            return -1  # silently drop; -1 signals "not stored" without raising

        key = text.strip().lower()[:80]

        if cross_session_dedup and session_id is not None:
            # Only dedup across sessions when we have a session_id to anchor to.
            # Sessionless calls (session_id=None) are anonymous/stateless — deduping
            # them against all prior sessions would silently suppress inserts with no
            # way for the caller to reason about which session owns the original row.
            existing = self.conn.execute(
                "SELECT id FROM learnings WHERE LOWER(SUBSTR(TRIM(text), 1, 80)) = ?",
                (key,),
            ).fetchone()
            if existing:
                return int(existing["id"])  # skip cross-session duplicate

        if session_id:
            existing = self.conn.execute(
                "SELECT id FROM learnings WHERE session_id = ? AND LOWER(SUBSTR(TRIM(text), 1, 80)) = ?",
                (session_id, key),
            ).fetchone()
            if existing:
                return int(existing["id"])  # skip within-session duplicate

        cursor = self.conn.execute(
            "INSERT INTO learnings (text, source, domain, importance, created_at, session_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (text, source, domain, importance,
             datetime.now(timezone.utc).isoformat(), session_id),
        )
        self.conn.commit()
        return cursor.lastrowid or -1

    def get_unpromoted(self, domain: str | None = None) -> list[dict[str, Any]]:
        """Get learnings not yet promoted to rules."""
        if domain:
            rows = self.conn.execute(
                "SELECT * FROM learnings WHERE promoted_to IS NULL AND domain = ? "
                "ORDER BY importance DESC",
                (domain,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM learnings WHERE promoted_to IS NULL "
                "ORDER BY importance DESC",
            ).fetchall()
        return [dict(r) for r in rows]

    def mark_promoted(self, learning_ids: list[int], rule_id: str) -> None:
        """Mark learnings as promoted to a rule."""
        if not learning_ids:
            return
        placeholders = ",".join("?" * len(learning_ids))
        self.conn.execute(
            f"UPDATE learnings SET promoted_to = ? WHERE id IN ({placeholders})",
            [rule_id, *learning_ids],
        )
        self.conn.commit()

    def get_decay_state(self, rule_id: str) -> DecayState:
        """Get FSRS decay state for a rule."""
        row = self.conn.execute(
            "SELECT * FROM rule_decay WHERE rule_id = ?", (rule_id,)
        ).fetchone()
        if row is None:
            return DecayState()
        return DecayState.from_dict(dict(row))

    def save_decay_state(self, rule_id: str, state: DecayState) -> None:
        """Save FSRS decay state for a rule."""
        d = state.to_dict()
        self.conn.execute(
            "INSERT OR REPLACE INTO rule_decay "
            "(rule_id, stability, difficulty, last_review, review_count, applied_count) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (rule_id, d["stability"], d["difficulty"],
             d["last_review"], d["review_count"], d["applied_count"]),
        )
        self.conn.commit()

    def count(self) -> dict[str, int]:
        """Get learning counts by domain."""
        rows = self.conn.execute(
            "SELECT domain, COUNT(*) as cnt FROM learnings GROUP BY domain"
        ).fetchall()
        return {r["domain"]: r["cnt"] for r in rows}

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None


# ─── Pattern Detector ──────────────────────────────────────────────────────

@dataclass
class PatternGroup:
    """A group of similar learnings that may warrant a rule."""
    representative: str        # Most common/central text
    members: list[dict[str, Any]]  # Learning dicts
    confidence: str            # low/medium/high
    count: int
    domain: str

    @property
    def should_promote(self) -> bool:
        """3+ occurrences = promote to rule."""
        return self.count >= 3


class PatternDetector:
    """Groups similar learnings and detects recurring patterns.

    Uses SequenceMatcher (difflib) for text similarity — no external
    dependencies needed. Threshold of 0.7 catches paraphrased versions
    of the same learning without over-grouping.
    """

    def __init__(self, similarity_threshold: float = 0.7):
        self.threshold = similarity_threshold

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text

    def _similarity(self, a: str, b: str) -> float:
        """Calculate text similarity ratio."""
        return SequenceMatcher(
            None, self._normalize(a), self._normalize(b)
        ).ratio()

    def detect(self, learnings: list[dict[str, Any]]) -> list[PatternGroup]:
        """Group similar learnings into patterns.

        Returns PatternGroups sorted by count (highest first).
        """
        if not learnings:
            return []

        groups: list[list[dict[str, Any]]] = []
        used: set[int] = set()

        for i, learning in enumerate(learnings):
            if i in used:
                continue

            group = [learning]
            used.add(i)

            for j, other in enumerate(learnings[i + 1:], start=i + 1):
                if j in used:
                    continue
                if self._similarity(learning["text"], other["text"]) >= self.threshold:
                    group.append(other)
                    used.add(j)

            groups.append(group)

        # Convert to PatternGroups
        results = []
        for group in groups:
            if len(group) < 2:
                continue  # Skip singletons

            # Representative = longest text (most detail)
            representative = max(group, key=lambda x: len(x["text"]))

            count = len(group)
            if count >= 10:
                confidence = "high"
            elif count >= 5:
                confidence = "medium"
            else:
                confidence = "low"

            domain = group[0].get("domain", "general")

            results.append(PatternGroup(
                representative=representative["text"],
                members=group,
                confidence=confidence,
                count=count,
                domain=domain,
            ))

        results.sort(key=lambda g: g.count, reverse=True)
        return results


# ─── Decay Engine ──────────────────────────────────────────────────────────

class DecayEngine:
    """Manages rule lifecycle: boost on use, archive on disuse.

    Uses FSRS-6 retrievability formula to determine which rules
    are still "remembered" by the system. Rules that drop below
    the archive threshold get flagged for removal.
    """

    def __init__(
        self,
        store: LearningStore,
        archive_threshold: float = 0.3,  # Below this = archive
        review_threshold: float = 0.7,   # Below this = needs review
    ):
        self.store = store
        self.archive_threshold = archive_threshold
        self.review_threshold = review_threshold

    def boost(self, rule_id: str) -> DecayState:
        """Boost a rule (it was successfully applied)."""
        state = self.store.get_decay_state(rule_id)
        state.boost()
        self.store.save_decay_state(rule_id, state)
        return state

    def check(self, rule_id: str) -> dict[str, Any]:
        """Check a rule's health. Returns status dict."""
        state = self.store.get_decay_state(rule_id)
        r = state.retrievability()

        if r < self.archive_threshold:
            status = "archive"
            recommendation = "Rule unused — consider archiving"
        elif r < self.review_threshold:
            status = "review"
            recommendation = "Rule fading — apply it or archive it"
        else:
            status = "healthy"
            recommendation = None

        return {
            "rule_id": rule_id,
            "retrievability": round(r, 3),
            "stability": round(state.stability, 3),
            "applied_count": state.applied_count,
            "status": status,
            "recommendation": recommendation,
        }

    def sweep(self, rule_ids: list[str]) -> dict[str, list[str]]:
        """Sweep all rules, categorize by health.

        Returns dict with 'healthy', 'review', 'archive' lists of rule_ids.
        """
        result: dict[str, list[str]] = {
            "healthy": [], "review": [], "archive": [],
        }
        for rule_id in rule_ids:
            status = self.check(rule_id)
            result[status["status"]].append(rule_id)
        return result
