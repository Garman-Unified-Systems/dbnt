"""DBNT Core - Rule encoding and dissonance calculation."""

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class RuleType(Enum):
    """Type of rule."""

    SUCCESS = "success"
    FAILURE = "failure"


class Category(Enum):
    """Rule categories."""

    # Success categories
    FORMAT = "format"  # Response structure that worked
    CODE = "code"  # Implementation patterns approved
    EXPLAIN = "explain"  # Right level of detail
    TOOL = "tool"  # Efficient tool combinations
    COMM = "comm"  # Communication style approved

    # Failure categories
    PROTOCOL = "protocol"  # Broke established pattern
    PREFERENCE = "preference"  # User corrected approach
    WASTE = "waste"  # Unnecessary verbosity
    GAP = "gap"  # Capability gap
    INTEGRATION = "integration"  # Systems didn't connect


@dataclass
class Rule:
    """A DBNT rule."""

    id: str
    type: RuleType
    category: Category
    pattern: str
    context: str
    weight: float = 1.0
    created: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_session: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "category": self.category.value,
            "pattern": self.pattern,
            "context": self.context,
            "weight": self.weight,
            "created": self.created.isoformat(),
            "source_session": self.source_session,
        }

    def to_markdown(self) -> str:
        """Export rule as markdown file content."""
        prefix = "Success" if self.type == RuleType.SUCCESS else "Failure"
        return f"""# {prefix}: {self.pattern[:50]}

**Category**: {self.category.value}
**Weight**: {self.weight}
**Created**: {self.created.strftime("%Y-%m-%d")}
**Source**: {self.source_session or "unknown"}

## Context

{self.context}

## Pattern

{self.pattern}

## When to Apply

[Auto-generated - edit as needed]
"""


@dataclass
class DissonanceResult:
    """Result of dissonance calculation."""

    score: float
    status: str
    success_count: int
    failure_count: int
    success_weight: float
    failure_weight: float
    recommendation: str | None = None


class RuleStore:
    """Storage for DBNT rules."""

    def __init__(self, base_path: Path | None = None):
        self.base_path = base_path or Path.home() / ".dbnt" / "rules"
        self.success_path = self.base_path / "successes"
        self.failure_path = self.base_path / "failures"
        self._ensure_paths()

    def _ensure_paths(self) -> None:
        """Create directories if they don't exist."""
        self.success_path.mkdir(parents=True, exist_ok=True)
        self.failure_path.mkdir(parents=True, exist_ok=True)

    def _generate_id(self, category: Category) -> str:
        """Generate a unique rule ID with collision prevention."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        suffix = secrets.token_hex(2)
        return f"{category.value}_{timestamp}_{suffix}"

    def save(self, rule: Rule) -> Path:
        """Save a rule to disk."""
        if rule.type == RuleType.SUCCESS:
            path = self.success_path / f"{rule.category.value}-{rule.id}.md"
        else:
            path = self.failure_path / f"{rule.category.value}-{rule.id}.md"

        path.write_text(rule.to_markdown())
        return path

    def load_all(self) -> list[Rule]:
        """Load all rules from disk."""
        from dbnt.storage.rules import load_rules_from_dir
        successes = load_rules_from_dir(self.success_path)
        failures = load_rules_from_dir(self.failure_path)
        return successes + failures

    def count(self) -> tuple[int, int]:
        """Count success and failure rules."""
        success_count = len(list(self.success_path.glob("*.md")))
        failure_count = len(list(self.failure_path.glob("*.md")))
        return success_count, failure_count


# Global store instance
_store: RuleStore | None = None


def get_store() -> RuleStore:
    """Get or create the global rule store."""
    global _store
    if _store is None:
        _store = RuleStore()
    return _store


def encode_success(
    category: str,
    pattern: str,
    context: str,
    weight: float = 1.5,
    session: str | None = None,
) -> Rule:
    """
    Encode a success pattern.

    Args:
        category: One of: format, code, explain, tool, comm
        pattern: What worked
        context: Why it worked / user feedback
        weight: Encoding weight (default 1.5 for success)
        session: Source session ID

    Returns:
        The created Rule
    """
    store = get_store()
    cat = Category(category)

    rule = Rule(
        id=store._generate_id(cat),
        type=RuleType.SUCCESS,
        category=cat,
        pattern=pattern,
        context=context,
        weight=weight,
        source_session=session,
    )

    store.save(rule)
    return rule


def encode_failure(
    category: str,
    pattern: str,
    context: str,
    weight: float = 1.0,
    session: str | None = None,
) -> Rule:
    """
    Encode a failure pattern.

    Args:
        category: One of: protocol, preference, waste, gap, integration
        pattern: What went wrong
        context: Why it failed / user feedback
        weight: Encoding weight (default 1.0 for failure)
        session: Source session ID

    Returns:
        The created Rule
    """
    store = get_store()
    cat = Category(category)

    rule = Rule(
        id=store._generate_id(cat),
        type=RuleType.FAILURE,
        category=cat,
        pattern=pattern,
        context=context,
        weight=weight,
        source_session=session,
    )

    store.save(rule)
    return rule


def get_rules() -> list[Rule]:
    """Get all rules."""
    return get_store().load_all()


def check_dissonance() -> DissonanceResult:
    """
    Calculate learning dissonance.

    Dissonance = |ideal_positive_rate - actual_positive_rate|

    Target: success rules should be 60% of total (inverted from typical)

    Returns:
        DissonanceResult with score, status, and recommendation
    """
    store = get_store()
    success_count, failure_count = store.count()
    total = success_count + failure_count

    if total == 0:
        return DissonanceResult(
            score=1.0,
            status="no_data",
            success_count=0,
            failure_count=0,
            success_weight=0.0,
            failure_weight=0.0,
            recommendation="Start encoding rules to build learning history",
        )

    # Calculate weighted totals (success at 1.5x)
    success_weight = success_count * 1.5
    failure_weight = failure_count * 1.0
    weighted_total = success_weight + failure_weight

    # Actual ratio using weights (success signals are 1.5x more valuable)
    actual_success_rate = success_weight / weighted_total

    # Target: 60% weighted success
    target_success_rate = 0.60
    dissonance = abs(target_success_rate - actual_success_rate)

    # Determine status
    if dissonance < 0.15:
        status = "balanced"
        recommendation = None
    elif dissonance < 0.30:
        status = "slight_imbalance"
        if actual_success_rate < target_success_rate:
            recommendation = "Encode more success patterns"
        else:
            recommendation = "Balance is good, continue as normal"
    elif dissonance < 0.50:
        status = "moderate_imbalance"
        recommendation = "Significant gap - actively seek success signals to encode"
    else:
        status = "severe_imbalance"
        recommendation = "System is anxiety-driven - prioritize success encoding immediately"

    return DissonanceResult(
        score=round(dissonance, 3),
        status=status,
        success_count=success_count,
        failure_count=failure_count,
        success_weight=round(success_weight, 2),
        failure_weight=round(failure_weight, 2),
        recommendation=recommendation,
    )
