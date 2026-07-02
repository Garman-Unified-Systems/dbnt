"""DBNT Transcript Extractor — turn session transcripts into learnings.

Regex-based extraction with no external dependencies.
For LLM-powered extraction, use the Ollama adapter (optional).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class LearningType(Enum):
    """Types of extracted learnings."""
    DECISION = "decision"
    PREFERENCE = "preference"
    MISTAKE = "mistake"
    APPROACH = "approach"
    CORRECTION = "correction"  # DBNT protocol signals


@dataclass
class ExtractedLearning:
    """A learning extracted from a transcript."""
    text: str
    type: LearningType
    importance: float  # 1-10
    source: str = "transcript"

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "type": self.type.value,
            "importance": self.importance,
            "source": self.source,
        }


# ─── Extraction Patterns ──────────────────────────────────────────────────

# DBNT correction signals (highest importance)
_CORRECTION_PATTERN = re.compile(
    r"(?:dbnt|dbnm|dbn|dbyc|db)\s*[-:]\s*"
    r"(?:Protocol|User Preference|Token Waste|Capability Gap|Integration|Security)"
    r"[:\s]+(.+?)(?:\n|$)",
    re.IGNORECASE,
)

# Explicit learnings ("learned:", "realized:", etc.)
_LEARNING_PATTERNS = [
    re.compile(r"(?:learned|discovered|found out|realized|insight):\s*(.+?)(?:\n|$)", re.IGNORECASE),
    re.compile(r"(?:pattern|observation):\s*(.+?)(?:\n|$)", re.IGNORECASE),
    re.compile(r"(?:key takeaway|lesson):\s*(.+?)(?:\n|$)", re.IGNORECASE),
]

# Decision patterns
_DECISION_PATTERN = re.compile(
    r"(?:decided to|chose to|will use|prefer|avoiding)\s+(.+?)(?:\.|$)",
    re.IGNORECASE,
)

# Mistake/correction patterns (from user messages)
_MISTAKE_PATTERNS = [
    re.compile(r"(?:that's wrong|that is wrong|no,?\s+)(.+?)(?:\.|$)", re.IGNORECASE),
    re.compile(r"(?:don't|do not|never|stop)\s+(.+?)(?:\.|$)", re.IGNORECASE),
]

# ─── Importance Scoring ───────────────────────────────────────────────────

_IMPORTANCE_WEIGHTS: list[tuple[list[str], int]] = [
    # (keywords, weight_delta)
    (["critical", "bug", "security", "breaking", "dbnt", "dbyc"], 3),
    (["pattern", "insight", "realized", "discovered", "architecture"], 2),
    (["error", "failed", "mistake", "wrong", "fix"], 2),
    (["decision", "chose", "selected", "prefer", "avoid"], 1),
    (["minor", "small", "trivial", "simple"], -2),
]


def _score_importance(text: str) -> float:
    """Score a learning's importance (1-10) based on keyword analysis."""
    score = 5
    text_lower = text.lower()
    for keywords, weight in _IMPORTANCE_WEIGHTS:
        if any(kw in text_lower for kw in keywords):
            score += weight
    return max(1, min(10, score))


# ─── Transcript Formatting ────────────────────────────────────────────────

def format_transcript(
    transcript_jsonl: str,
    max_chars: int = 8000,
) -> str:
    """Format a Claude Code JSONL transcript into readable text.

    Filters to user/assistant messages, truncates tool results,
    and caps total length with a first-20%/last-80% strategy.

    Args:
        transcript_jsonl: Raw JSONL string (one JSON object per line)
        max_chars: Maximum output characters

    Returns:
        Formatted transcript text
    """
    lines = []
    for raw_line in transcript_jsonl.strip().split("\n"):
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            entry = json.loads(raw_line)
        except json.JSONDecodeError:
            continue

        msg = entry.get("message", entry)
        role = msg.get("role", entry.get("type", ""))
        if role not in ("user", "assistant"):
            continue

        content = msg.get("content", "")
        if isinstance(content, str):
            lines.append(f"{role}: {content}")
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, str):
                    lines.append(f"{role}: {block}")
                elif isinstance(block, dict):
                    btype = block.get("type", "")
                    if btype == "text":
                        lines.append(f"{role}: {block.get('text', '')}")
                    elif btype == "thinking":
                        continue  # Skip thinking blocks
                    elif btype == "tool_use":
                        name = block.get("name", "unknown")
                        inp = json.dumps(block.get("input", {}))[:200]
                        lines.append(f"{role}: [tool_use: {name}({inp})]")
                    elif btype == "tool_result":
                        result_text = str(block.get("content", ""))[:500]
                        lines.append(f"{role}: [tool_result: {result_text}]")

    text = "\n".join(lines)

    if len(text) > max_chars:
        # Keep first 20% + last 80%
        first = int(max_chars * 0.2)
        last = max_chars - first
        text = text[:first] + "\n\n...[middle truncated]...\n\n" + text[-last:]

    return text


# ─── Main Extraction ──────────────────────────────────────────────────────

def extract_from_text(text: str) -> list[ExtractedLearning]:
    """Extract learnings from plain text using regex patterns.

    This is the no-dependency extraction path. For LLM-powered extraction,
    see `extract_with_ollama()`.

    Args:
        text: Session transcript or any text containing learnings

    Returns:
        List of ExtractedLearning objects, deduplicated
    """
    results: list[ExtractedLearning] = []
    seen: set[str] = set()

    def _add(text: str, ltype: LearningType, importance: float | None = None) -> None:
        text = text.strip()
        if len(text) < 15:
            return
        # Simple dedup by normalized text
        key = text.lower()[:80]
        if key in seen:
            return
        seen.add(key)
        results.append(ExtractedLearning(
            text=text,
            type=ltype,
            importance=importance or _score_importance(text),
        ))

    # 1. DBNT correction signals (highest priority)
    for match in _CORRECTION_PATTERN.finditer(text):
        _add(match.group(1), LearningType.CORRECTION, importance=8)

    # 2. Explicit learnings
    for pattern in _LEARNING_PATTERNS:
        for match in pattern.finditer(text):
            _add(match.group(1), LearningType.APPROACH)

    # 3. Decisions
    for match in _DECISION_PATTERN.finditer(text):
        _add(f"Decision: {match.group(1)}", LearningType.DECISION)

    # 4. Mistakes/corrections from user
    for pattern in _MISTAKE_PATTERNS:
        for match in pattern.finditer(text):
            _add(match.group(1), LearningType.MISTAKE)

    return results


def extract_from_transcript(transcript_jsonl: str) -> list[ExtractedLearning]:
    """Extract learnings from a Claude Code JSONL transcript.

    Formats the transcript, then runs regex extraction.

    Args:
        transcript_jsonl: Raw JSONL transcript string

    Returns:
        List of ExtractedLearning objects
    """
    text = format_transcript(transcript_jsonl)
    return extract_from_text(text)


# ─── Ollama-Powered Extraction (Optional) ─────────────────────────────────

_OLLAMA_PROMPT = """You are a memory extraction agent reviewing a session transcript.
Extract 0-5 patterns worth remembering ACROSS FUTURE sessions. Each pattern must be actionable in a FUTURE session — not just a record of what happened.

Extract ONLY:
- User preferences expressed explicitly or implicitly (communication style, tool choices, workflow habits)
- Recurring workflow patterns the user follows or expects
- Mistakes corrected by the user (any "no", "that's wrong", "fix this", DB/DBYC signals) — phrase as what TO DO, not just what went wrong
- Tool usage patterns and confirmed working approaches
- Architectural decisions that apply across sessions (not one-time implementation details)

Do NOT extract:
- Completion status ("v2.6 complete", "migration done")
- Version numbers or release notes
- One-time events or session-specific observations
- Vague labels without actionable detail
- Project-specific implementation details (file names, function names, variable names)

Output ONLY a JSON array. Each item: {{"pattern": "...", "type": "decision|preference|mistake|approach", "confidence": 0.0-1.0}}
If nothing notable: []

TRANSCRIPT:
{transcript}"""

_VALID_TYPES = {"decision", "preference", "mistake", "approach"}


def extract_with_ollama(
    text: str,
    base_url: str = "http://127.0.0.1:11434",
    model: str = "llama3.2:3b",
) -> list[ExtractedLearning]:
    """Extract learnings using a local Ollama model.

    Requires Ollama running locally. Falls back to regex extraction on failure.

    Args:
        text: Formatted transcript text (use format_transcript() first)
        base_url: Ollama API base URL
        model: Ollama model name

    Returns:
        List of ExtractedLearning objects
    """
    import urllib.error
    import urllib.request

    prompt = _OLLAMA_PROMPT.format(transcript=text[:8000])

    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 1024},
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            response_text = result.get("response", "")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        # Ollama unavailable — fall back to regex
        return extract_from_text(text)

    # Parse JSON response
    patterns = _parse_ollama_response(response_text)

    return [
        ExtractedLearning(
            text=p["pattern"],
            type=LearningType(p["type"]),
            importance=_score_importance(p["pattern"]),
            source="ollama",
        )
        for p in patterns
    ]


def _parse_ollama_response(text: str) -> list[dict[str, Any]]:
    """Parse Ollama JSON response with fallbacks."""
    # Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)

    # Try direct parse
    try:
        data = json.loads(text.strip())
        if isinstance(data, list):
            return _validate_patterns(data)
    except json.JSONDecodeError:
        pass

    # Regex fallback — find array in text
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, list):
                return _validate_patterns(data)
        except json.JSONDecodeError:
            pass

    return []


def _validate_patterns(patterns: list[Any]) -> list[dict[str, Any]]:
    """Validate and normalize extracted patterns."""
    valid = []
    for p in patterns:
        if not isinstance(p, dict):
            continue
        pattern = p.get("pattern", "").strip()
        if len(pattern) < 10:
            continue

        ptype = p.get("type", "decision")
        if ptype not in _VALID_TYPES:
            ptype = "decision"

        confidence = p.get("confidence", 0.5)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (ValueError, TypeError):
            confidence = 0.5

        valid.append({
            "pattern": pattern,
            "type": ptype,
            "confidence": confidence,
        })

    return valid[:5]
