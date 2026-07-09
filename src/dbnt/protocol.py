"""DBNT Protocol - Feedback command routing and scoring."""

from __future__ import annotations

import contextlib
import json
import math
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class Command(Enum):
    """DBNT command levels (escalating severity)."""
    DB = "db"           # Do Better - recoverable
    DBN = "dbn"         # Do Better Now - same mistake
    DBNM = "dbnm"       # Do Better Now Move - fix and continue
    DBYC = "dbyc"       # Critical - human took over
    GOOD = "good"       # Confirmed working
    TWEAK = "tweak"     # Close, iterate
    NONE = "none"       # No command detected


class Action(Enum):
    """Required action after command detection."""
    ENCODE_SUCCESS = "encode_success"
    ENCODE_FAILURE = "encode_failure"
    ENCODE_BOTH = "encode_both"      # DBYC: encode failure AND success
    ITERATE = "iterate"               # Tweak: try again
    ACKNOWLEDGE = "acknowledge"       # Good: log and continue
    NONE = "none"


@dataclass
class ProtocolResponse:
    """Response from protocol command detection."""
    command: Command
    action: Action
    points: float
    response_text: str
    should_encode: bool = False


class ScoreStateSchemaError(ValueError):
    """Raised when decoded score JSON does not satisfy the persisted schema."""


@dataclass
class ScoreState:
    """Persistent scoring state."""
    total_points: float = 0.0
    events: list[dict[str, Any]] = field(default_factory=list)
    tweak_count: int = 0  # Track consecutive tweaks

    def add_event(self, command: Command, points: float) -> None:
        self.total_points += points
        self.events.append({
            "command": command.value,
            "points": points,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    @property
    def success_count(self) -> int:
        return sum(
            1 for e in self.events
            if e.get("points", e.get("delta", e.get("score", e.get("weight", 0)))) > 0
        )

    @property
    def failure_count(self) -> int:
        return sum(
            1 for e in self.events
            if e.get("points", e.get("delta", e.get("score", e.get("weight", 0)))) < 0
        )

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total


# Command detection patterns
# These are designed for SHORT directive messages, not natural language parsing.
# For NL signal detection, use signals.detector instead.
_PATTERNS: list[tuple[Command, re.Pattern[str]]] = [
    # Order matters: most specific first
    # DB-family commands must appear at START of message to avoid false positives
    (Command.DBYC, re.compile(r"^\s*dbyc(?:\s|$|[.!])", re.IGNORECASE)),
    (Command.DBNM, re.compile(r"^\s*dbnm(?:\s|$|[.!])", re.IGNORECASE)),
    (Command.DBN, re.compile(r"^\s*dbn(?:\s|$|[.!])", re.IGNORECASE)),
    (Command.DB, re.compile(r"^\s*db(?:\s|$|[.!])", re.IGNORECASE)),
    (Command.GOOD, re.compile(
        r"(?:^|\s)(fixed|ship\s*it|nailed\s*it)(?:\s|$|[.!])", re.IGNORECASE
    )),
    (Command.TWEAK, re.compile(
        r"(?:^|\s)(tweak)(?:\s|$|[.!])", re.IGNORECASE
    )),
]

# Points table
_POINTS: dict[Command, float] = {
    Command.DB: -1.0,
    Command.DBN: -1.0,
    Command.DBNM: -1.0,
    Command.DBYC: -2.0,
    Command.GOOD: 2.0,
    Command.TWEAK: 0.5,  # First time; degrades after
}

# Actions table
_ACTIONS: dict[Command, Action] = {
    Command.DB: Action.ENCODE_SUCCESS,       # Fix + encode what works
    Command.DBN: Action.ENCODE_SUCCESS,      # Same, faster
    Command.DBNM: Action.ENCODE_SUCCESS,     # Fix, encode, move on
    Command.DBYC: Action.ENCODE_BOTH,        # Encode failure AND success
    Command.GOOD: Action.ACKNOWLEDGE,
    Command.TWEAK: Action.ITERATE,
}

# Response text
_RESPONSES: dict[Command, str] = {
    Command.DB: "Yes Chef! Fixing and encoding the correct pattern.",
    Command.DBN: "Yes Chef! On it — same fix, faster.",
    Command.DBNM: "Yes Chef! Fixed, encoded, moving on.",
    Command.DBYC: "Yes Chef! Encoding both the failure and the fix.",
    Command.GOOD: "Confirmed. +3 logged.",
    Command.TWEAK: "Iterating.",
}


class Protocol:
    """DBNT feedback protocol engine.

    Detects commands from human text, routes to handlers,
    tracks score, and returns required actions.

    Usage:
        protocol = Protocol()
        response = protocol.process("dbnm")
        if response.action == Action.ENCODE_SUCCESS:
            # encode what worked
            ...
    """

    def __init__(self, state_dir: Path | None = None):
        self.state_dir = state_dir or Path.home() / ".dbnt"
        self.score_path = self.state_dir / "score.json"
        self._state: ScoreState | None = None

    @property
    def state(self) -> ScoreState:
        if self._state is None:
            self._state = self._load_state()
        return self._state

    def process(self, text: str) -> ProtocolResponse:
        """Process user text for DBNT commands.

        Returns ProtocolResponse with command, action, points, and response text.
        """
        command = self._detect_command(text)

        if command == Command.NONE:
            return ProtocolResponse(
                command=Command.NONE,
                action=Action.NONE,
                points=0.0,
                response_text="",
            )

        points = self._calculate_points(command)
        action = _ACTIONS[command]
        response_text = _RESPONSES[command]

        # Update state
        self.state.add_event(command, points)
        if command == Command.TWEAK:
            self.state.tweak_count += 1
        elif command == Command.GOOD:
            self.state.tweak_count = 0  # Reset on success

        self._save_state()

        return ProtocolResponse(
            command=command,
            action=action,
            points=points,
            response_text=response_text,
            should_encode=action in (
                Action.ENCODE_SUCCESS,
                Action.ENCODE_FAILURE,
                Action.ENCODE_BOTH,
            ),
        )

    def _detect_command(self, text: str) -> Command:
        """Detect DBNT command from text."""
        text = text.strip()
        for command, pattern in _PATTERNS:
            if pattern.search(text):
                return command
        return Command.NONE

    def _calculate_points(self, command: Command) -> float:
        """Calculate points, handling tweak degradation."""
        base = _POINTS[command]
        if command == Command.TWEAK and self.state.tweak_count > 0:
            # First tweak = +0.5, subsequent = -1 each
            return -1.0 * self.state.tweak_count
        if command == Command.GOOD:
            # Success weighted 1.5x
            return base * 1.5  # +3.0 effective
        return base

    def _load_state(self) -> ScoreState:
        """Load score state from disk."""
        if not self.score_path.exists():
            return ScoreState()
        try:
            data = json.loads(self.score_path.read_text())
            if not isinstance(data, dict):
                raise ScoreStateSchemaError("score state must be a JSON object")

            total_points = _score_number(data.get("total_points", 0.0), "total_points")
            events = _score_events(data.get("events", []))
            tweak_count = _nonnegative_count(data.get("tweak_count", 0), "tweak_count")
            return ScoreState(
                total_points=total_points,
                events=events,
                tweak_count=tweak_count,
            )
        except (json.JSONDecodeError, OSError, ScoreStateSchemaError) as exc:
            self._quarantine_corrupt_score(exc)
            return ScoreState()

    def _save_state(self) -> None:
        """Persist score state to disk."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "total_points": self.state.total_points,
            "events": self.state.events,
            "tweak_count": self.state.tweak_count,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        tmp_path = self.score_path.with_name(f"{self.score_path.name}.{os.getpid()}.tmp")
        tmp_path.write_text(json.dumps(data, indent=2))
        tmp_path.replace(self.score_path)

    def _quarantine_corrupt_score(self, exc: Exception) -> None:
        """Move an unreadable score file aside before starting fresh."""
        if not self.score_path.exists():
            return

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        quarantine_path = self.score_path.with_name(
            f"{self.score_path.name}.corrupt-{timestamp}-{os.getpid()}"
        )
        try:
            self.score_path.replace(quarantine_path)
        except OSError:
            return

        note_path = quarantine_path.with_name(f"{quarantine_path.name}.reason")
        with contextlib.suppress(OSError):
            note_path.write_text(f"{type(exc).__name__}: {exc}\n")


def _score_number(value: object, field_name: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ScoreStateSchemaError(f"{field_name} must be a finite number")
    return float(value)


def _nonnegative_count(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ScoreStateSchemaError(f"{field_name} must be a nonnegative integer")
    return value


def _score_events(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ScoreStateSchemaError("events must be an array")

    events: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ScoreStateSchemaError(f"events[{index}] must be an object")
        event: dict[str, Any] = dict(item)
        for numeric_field in ("points", "delta", "score", "weight"):
            if numeric_field in event:
                _score_number(event[numeric_field], f"events[{index}].{numeric_field}")
        if "points" not in event and "delta" in event:
            event = {
                **event,
                "points": event["delta"],
                "command": event.get("event", "unknown"),
            }
        events.append(event)
    return events
