"""Seat rule slices — per-runner lesson storage under ``rules/seats/<seat>/``."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from dbnt.core import Category, Rule, RuleType
from dbnt.state import resolve_state_root
from dbnt.storage.rules import load_rules_from_dir, parse_rule_file

if TYPE_CHECKING:
    from pathlib import Path

SEAT_CATEGORIES: dict[RuleType, tuple[str, ...]] = {
    RuleType.SUCCESS: ("format", "code", "explain", "tool", "comm"),
    RuleType.FAILURE: ("protocol", "preference", "waste", "gap", "integration"),
}

_MAX_SEAT_LENGTH = 128
_SLUG_LENGTH = 40
_SEAT_SEGMENT = r"[a-z0-9][a-z0-9._-]*"
_SEAT_PATTERN = re.compile(rf"^{_SEAT_SEGMENT}@{_SEAT_SEGMENT}$")
_SLUG_STRIP = re.compile(r"[^a-z0-9]+")

_DEFAULT_WEIGHT: dict[RuleType, float] = {RuleType.SUCCESS: 1.5, RuleType.FAILURE: 1.0}
_DEFAULT_CONTEXT: dict[RuleType, str] = {
    RuleType.SUCCESS: "User approved this pattern",
    RuleType.FAILURE: "This pattern caused issues",
}
_SLICE_NAMES: dict[RuleType, str] = {RuleType.SUCCESS: "successes", RuleType.FAILURE: "failures"}


class SeatError(ValueError):
    """Raised when a seat identifier, category, or pattern cannot be stored."""


@dataclass
class SeatCapture:
    """Result of writing one rule into a seat slice."""

    rule: Rule
    path: Path
    replaced: bool


def validate_seat(seat: str) -> str:
    """Return the seat unchanged after confirming it names exactly one slice directory."""
    if not seat or not seat.strip():
        raise SeatError("seat must not be empty")
    if seat != seat.strip():
        raise SeatError(f"seat must not carry surrounding whitespace: {seat!r}")
    if ".." in seat:
        raise SeatError(f"seat must not contain path traversal: {seat!r}")
    if "/" in seat or "\\" in seat:
        raise SeatError(f"seat must not contain path separators: {seat!r}")
    if len(seat) > _MAX_SEAT_LENGTH:
        raise SeatError(f"seat must be at most {_MAX_SEAT_LENGTH} characters: {seat!r}")
    if not _SEAT_PATTERN.match(seat):
        raise SeatError(f"seat must look like name@node in lowercase ASCII: {seat!r}")
    return seat


def seat_rules_dir(seat: str, root: str | Path | None = None) -> Path:
    """Resolve the slice directory for a seat under the active state root."""
    return resolve_state_root(root) / "rules" / "seats" / validate_seat(seat)


def resolve_category(kind: RuleType | str, category: str) -> Category:
    """Return the category after confirming it belongs to the requested direction."""
    rule_type = RuleType(kind)
    allowed = SEAT_CATEGORIES[rule_type]
    if category not in allowed:
        raise SeatError(
            f"category {category!r} is not valid for {rule_type.value}; "
            f"choose from {', '.join(allowed)}"
        )
    return Category(category)


def capture_seat_rule(
    seat: str,
    pattern: str,
    kind: RuleType | str,
    category: str,
    context: str = "",
    root: str | Path | None = None,
    replace_existing: bool = False,
) -> SeatCapture:
    """Write one rule into a seat slice, refusing to duplicate an existing pattern."""
    rule_type = RuleType(kind)
    resolved = resolve_category(rule_type, category)
    normalized = pattern.strip()
    if not normalized:
        raise SeatError("pattern must not be empty")

    slice_dir = seat_rules_dir(seat, root) / _SLICE_NAMES[rule_type]
    path = slice_dir / f"{resolved.value}-{_pattern_slug(normalized)}-{_pattern_key(normalized)}.md"
    existing = parse_rule_file(path) if path.is_file() else None
    if existing is not None and not replace_existing:
        raise SeatError(f"seat rule already exists: {path} (pass --replace to update it)")

    rule = _build_rule(path, rule_type, resolved, normalized, context, existing)
    slice_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(rule.to_markdown())
    return SeatCapture(rule=rule, path=path, replaced=existing is not None)


def list_seat_names(root: str | Path | None = None) -> list[str]:
    """List every seat that has a slice directory, sorted by name."""
    base = resolve_state_root(root) / "rules" / "seats"
    if not base.is_dir():
        return []
    return sorted(path.name for path in base.iterdir() if path.is_dir())


def load_seat_rules(seat: str, root: str | Path | None = None) -> list[Rule]:
    """Load every rule in a seat slice; a missing slice yields an empty list."""
    base = seat_rules_dir(seat, root)
    successes = _load_slice(base / _SLICE_NAMES[RuleType.SUCCESS], RuleType.SUCCESS)
    failures = _load_slice(base / _SLICE_NAMES[RuleType.FAILURE], RuleType.FAILURE)
    return successes + failures


def decay_key(seat: str, rule_id: str) -> str:
    """Return the decay-store key for a seat rule, namespaced by seat."""
    return f"{validate_seat(seat)}/{rule_id}"


def render_prompt_block(seat: str, rules: list[Rule]) -> str:
    """Render a seat's rules as a markdown block for an agent instruction file."""
    lines = [f"## Seat rules: {validate_seat(seat)}", ""]
    if not rules:
        lines.append("_No seat rules captured yet._")
        return "\n".join(lines)
    lines.extend(f"- [{rule.type.value}/{rule.category.value}] {rule.pattern}" for rule in rules)
    return "\n".join(lines)


def _load_slice(directory: Path, expected: RuleType) -> list[Rule]:
    return [replace(rule, type=expected) for rule in load_rules_from_dir(directory)]


def _build_rule(
    path: Path,
    rule_type: RuleType,
    category: Category,
    pattern: str,
    context: str,
    existing: Rule | None,
) -> Rule:
    return Rule(
        id=path.stem,
        type=rule_type,
        category=category,
        pattern=pattern,
        context=context.strip() or _DEFAULT_CONTEXT[rule_type],
        weight=existing.weight if existing is not None else _DEFAULT_WEIGHT[rule_type],
        created=existing.created if existing is not None else datetime.now(timezone.utc),
    )


def _pattern_key(pattern: str) -> str:
    normalized = " ".join(pattern.split()).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:8]


def _pattern_slug(pattern: str) -> str:
    slug = _SLUG_STRIP.sub("-", pattern.lower()).strip("-")
    return slug[:_SLUG_LENGTH].strip("-") or "rule"
