"""Markdown rule file storage — read and write DBNT rules."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from dbnt.core import Category, Rule, RuleType

if TYPE_CHECKING:
    from pathlib import Path


def parse_rule_file(path: Path) -> Rule | None:
    """Parse a markdown rule file back into a Rule object.

    Supports two formats:
    1. Frontmatter format (---/--- delimited YAML-like header)
    2. Heading format (# Rule: Name / # Success: Name / # Failure: Name)

    Returns None if the file can't be parsed.
    """
    try:
        content = path.read_text()
    except OSError:
        return None

    # Extract metadata from frontmatter or headings
    rule_type = _detect_type(path, content)
    category = _detect_category(path, content)
    rule_id = path.stem

    # Extract key sections
    pattern = _extract_section(content, "Pattern") or _extract_section(content, "Pattern to Avoid") or _extract_section(content, "Pattern That Worked") or ""
    context = _extract_section(content, "Context") or _extract_section(content, "Trigger") or ""

    # If no structured sections, use the whole body as context
    if not pattern and not context:
        # Strip the heading and use rest as context
        lines = content.strip().split("\n")
        context = "\n".join(lines[1:]).strip()
        pattern = lines[0].lstrip("# ") if lines else ""

    # Extract dates
    created = _extract_date(content) or datetime.now(timezone.utc)
    source = _extract_field(content, "Source") or _extract_field(content, "Session")

    # Extract weight
    weight_str = _extract_field(content, "Weight")
    weight = float(weight_str) if weight_str else (1.5 if rule_type == RuleType.SUCCESS else 1.0)

    return Rule(
        id=rule_id,
        type=rule_type,
        category=category,
        pattern=pattern,
        context=context,
        weight=weight,
        created=created,
        source_session=source,
    )


def load_rules_from_dir(directory: Path) -> list[Rule]:
    """Load all rule files from a directory."""
    rules: list[Rule] = []
    if not directory.exists():
        return rules
    for path in sorted(directory.glob("*.md")):
        rule = parse_rule_file(path)
        if rule:
            rules.append(rule)
    return rules


def _detect_type(path: Path, content: str) -> RuleType:
    """Detect rule type from path or content."""
    path_str = str(path).lower()
    if "success" in path_str:
        return RuleType.SUCCESS
    if "failure" in path_str or "fail" in path_str:
        return RuleType.FAILURE

    content_lower = content.lower()
    if content_lower.startswith("# success"):
        return RuleType.SUCCESS
    if "## pattern that worked" in content_lower:
        return RuleType.SUCCESS

    return RuleType.FAILURE  # Default to failure (conservative)


def _detect_category(path: Path, content: str) -> Category:
    """Detect category from path stem or content."""
    stem = path.stem.lower()

    # Try matching stem prefix to category
    for cat in Category:
        if stem.startswith(cat.value):
            return cat

    # Try matching content
    content_lower = content.lower()
    if any(w in content_lower for w in ["protocol", "broke", "established pattern"]):
        return Category.PROTOCOL
    if any(w in content_lower for w in ["preference", "corrected", "approach"]):
        return Category.PREFERENCE
    if any(w in content_lower for w in ["code", "implementation", "function"]):
        return Category.CODE

    return Category.PROTOCOL  # Default


def _extract_section(content: str, heading: str) -> str | None:
    """Extract content under a markdown heading."""
    pattern = rf"##\s*{re.escape(heading)}\s*\n(.*?)(?=\n##|\Z)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_field(content: str, field: str) -> str | None:
    """Extract a **Field**: value or **Field:** value."""
    pattern = rf"\*\*{re.escape(field)}\*\*:?\s*(.+)"
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _extract_date(content: str) -> datetime | None:
    """Extract a date from content."""
    # Try ISO format
    match = re.search(r"(\d{4}-\d{2}-\d{2})", content)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return None
