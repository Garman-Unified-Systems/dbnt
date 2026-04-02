# Yellow Paper -- DBNT

> Notion: https://www.notion.so/331b18c770b28109a81bf5dbfdb63d99

## Protocol Commands

The DBNT protocol defines an escalating correction ladder. Each command has a fixed severity, point value, required action, and expected agent response.

| Command | Full Name | Points | Action | Agent Response |
|---------|-----------|--------|--------|----------------|
| `db` | Do Better | -1 | encode_success | "Yes Chef!" + fix + encode success pattern |
| `dbn` | Do Better Now | -1 | encode_success | "Yes Chef!" + fix faster + encode |
| `dbnm` | Do Better Now Move | -1 | encode_success | "Yes Chef!" + fix + encode + continue |
| `dbyc` | Critical (Director took over) | -2 | encode_both | "Yes Chef!" + encode failure AND success |
| `good` / `fixed` / `ship it` | Confirmed working | +2 (x1.5 = +3) | acknowledge | Log success |
| `tweak` / `almost` | Close, iterate | +0.5 first, -1*N after | iterate | Adjust and retry |

### Command Detection

Commands are detected via anchored regex at the start of messages. Order: most specific first (DBYC > DBNM > DBN > DB). This prevents `dbn` from matching inside `dbnm`.

```python
# Detection patterns (evaluated in order)
r"^\s*dbyc(?:\s|$|[.!])"     # Must be at start of message
r"^\s*dbnm(?:\s|$|[.!])"
r"^\s*dbn(?:\s|$|[.!])"
r"^\s*db(?:\s|$|[.!])"
r"(?:^|\s)(fixed|ship\s*it|nailed\s*it)(?:\s|$|[.!])"   # Can appear anywhere
r"(?:^|\s)(tweak)(?:\s|$|[.!])"
```

### Tweak Degradation

The `tweak` command has progressive scoring:
- First occurrence: +0.5 points
- Subsequent: -1.0 * tweak_count
- Resets to 0 on next `good`/`fixed` signal

This prevents infinite iteration loops where the agent keeps "almost" getting it right.

## Signal Detection

Natural language signals are classified without requiring protocol commands. Signals are regex-matched, case-insensitive, evaluated in priority order.

| Category | Examples | Weight | Encoding |
|----------|----------|--------|----------|
| POSITIVE_STRONG | "perfect", "ship it", "nailed it", "exactly right" | 1.5x | Yes |
| POSITIVE_MODERATE | "great", "nice", "good job", "that works" | 1.2x | Yes |
| NEUTRAL | "ok", "sure", "fine", "k" | 0.0 | No |
| NEGATIVE_MODERATE | "hmm", "not quite", "try again", "close but" | 0.8x | Yes |
| NEGATIVE_STRONG | "wrong", "broken", "fix this", "doesn't work" | 1.0x | Yes (failure) |

Silence = neutral approval. The system does not require active positive feedback to function.

### Signal Data Structure

```python
@dataclass
class Signal:
    type: SignalType          # POSITIVE | NEGATIVE | NEUTRAL
    strength: SignalStrength  # STRONG | MODERATE | WEAK
    match: str | None         # The regex match that triggered detection
    weight: float             # Encoding weight (0.0 - 1.5)

    def should_encode(self) -> bool:
        # Only STRONG and MODERATE signals with non-NEUTRAL type
        ...
```

## Scoring System

Protocol score tracks cumulative agent performance.

```python
@dataclass
class ScoreState:
    total_points: float       # Running total
    events: list[dict]        # {command, points, timestamp}
    tweak_count: int          # Consecutive tweaks (for degradation)
```

**Success rate** = events with positive points / (positive + negative events). Target: 98%+.

**Persistence:** JSON at `~/.dbnt/score.json`. Legacy migration handles `delta` -> `points` key rename transparently.

## Data Structures

### Rule

```python
@dataclass
class Rule:
    id: str                   # "{category}_{timestamp}_{hex4}" e.g. "code_20260315_a1b2"
    type: RuleType            # SUCCESS | FAILURE
    category: Category        # format|code|explain|tool|comm|protocol|preference|waste|gap|integration
    pattern: str              # What worked or failed
    context: str              # Why / user feedback
    weight: float             # 1.5 (success) or 1.0 (failure)
    created: datetime         # UTC
    source_session: str|None  # Session ID
```

### Rule Categories

| Type | Category | Description |
|------|----------|-------------|
| Success | format | Response structure that worked |
| Success | code | Implementation pattern approved |
| Success | explain | Right level of detail |
| Success | tool | Efficient tool combinations |
| Success | comm | Communication style approved |
| Failure | protocol | Broke established pattern |
| Failure | preference | User corrected approach |
| Failure | waste | Unnecessary verbosity |
| Failure | gap | Capability gap |
| Failure | integration | Systems didn't connect |

### Rule Markdown Format

```markdown
# Success: Always use timezone-aware datetimes

**Category**: code
**Weight**: 1.5
**Created**: 2026-03-15
**Source**: session_abc123

## Context
Three separate corrections on datetime handling across different projects.
Auto-promoted from pattern after 3+ occurrences.

## Pattern
Always use timezone-aware datetime objects. Store in UTC, display in local time.

## When to Apply
[Auto-generated - edit as needed]
```

### FSRS-6 Decay State

```python
@dataclass
class DecayState:
    stability: float      # Days until retrievability drops to 90% (default 1.0)
    difficulty: float     # 0.0 (easy) to 1.0 (hard) (default 0.5)
    last_review: datetime | None
    review_count: int
    applied_count: int
```

**Retrievability formula:**
```
R(t, S) = (1 + t / (9 * S))^(-1)
```
Where `t` = elapsed days since last application, `S` = stability.

**Stability update on review:**

| Rating | Meaning | Stability Change | Difficulty Change |
|--------|---------|-----------------|-------------------|
| 1 (forgot) | Rule not applied when it should have been | *0.5 | +0.1 |
| 2 (hard) | Applied with difficulty | *0.8 | +0.05 |
| 3 (good) | Applied correctly | *(1 + 0.5*(1-difficulty)) | -0.05 |
| 4 (easy) | Applied effortlessly | *(1 + 1.0*(1-difficulty)) | -0.1 |

**Sweep thresholds:**
- Healthy: retrievability >= 0.7
- Review: 0.3 <= retrievability < 0.7
- Archive: retrievability < 0.3

### Dissonance Calculation

```
actual_success_rate = (success_count * 1.5) / (success_count * 1.5 + failure_count * 1.0)
dissonance = |0.60 - actual_success_rate|
```

Target: 60% weighted success. Status tiers: balanced (<0.15), slight_imbalance (<0.30), moderate_imbalance (<0.50), severe_imbalance (>=0.50).

### Learning Store Schema (SQLite)

```sql
CREATE TABLE learnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    source TEXT DEFAULT 'unknown',
    domain TEXT DEFAULT 'general',
    importance REAL DEFAULT 1.0,
    created_at TEXT NOT NULL,           -- ISO 8601 UTC
    session_id TEXT,
    promoted_to TEXT                     -- rule ID if promoted
);

CREATE TABLE rule_decay (
    rule_id TEXT PRIMARY KEY,
    stability REAL DEFAULT 1.0,
    difficulty REAL DEFAULT 0.5,
    last_review TEXT,                    -- ISO 8601 UTC
    review_count INTEGER DEFAULT 0,
    applied_count INTEGER DEFAULT 0
);

-- Indexes
CREATE INDEX idx_learnings_domain ON learnings(domain);
CREATE INDEX idx_learnings_promoted ON learnings(promoted_to);
CREATE INDEX idx_learnings_session_text ON learnings(session_id);
CREATE INDEX idx_learnings_dedup_key ON learnings(LOWER(SUBSTR(TRIM(text), 1, 80)));
```

### Pattern Detection

- **Algorithm:** Pairwise SequenceMatcher (difflib) on normalized text
- **Similarity threshold:** 0.7 (catches paraphrases without over-grouping)
- **Normalization:** lowercase, strip, remove punctuation, collapse whitespace
- **Promotion threshold:** 3+ members in a group
- **Confidence:** low (<5), medium (5-9), high (10+)
- **Complexity:** O(n^2). Capped at 200 learnings by default.

### Contamination Filter

Learnings matching these patterns are silently dropped:

```
^Use tool_use:
^Use Bash to run
respond to these messages or otherwise consider
system.reminder
<system-reminder>
IMPORTANT:.*after completing
task.notification
```

This prevents Claude Code's internal system prompts from being stored as "learnings."

## API Surface

### Python API

| Function | Input | Output | Description |
|----------|-------|--------|-------------|
| `Protocol().process(text)` | str | ProtocolResponse | Detect command, route action, update score |
| `detect_signal(text)` | str | Signal | Classify natural language feedback |
| `encode_success(category, pattern, context)` | str, str, str | Rule | Write success rule to disk |
| `encode_failure(category, pattern, context)` | str, str, str | Rule | Write failure rule to disk |
| `check_dissonance()` | -- | DissonanceResult | Calculate success/failure balance |
| `get_rules()` | -- | list[Rule] | Load all rules from disk |
| `LearningStore().add(text, ...)` | str + kwargs | int | Store a learning, returns ID |
| `PatternDetector().detect(learnings)` | list[dict] | list[PatternGroup] | Group similar learnings |
| `DecayEngine(store).boost(rule_id)` | str | DecayState | Boost rule after application |
| `DecayEngine(store).sweep(rule_ids)` | list[str] | dict[str, list[str]] | Categorize rules by health |
| `extract_from_text(text)` | str | list[ExtractedLearning] | Regex-based transcript extraction |
| `extract_from_transcript(jsonl)` | str | list[ExtractedLearning] | JSONL transcript -> learnings |
| `extract_with_ollama(text, ...)` | str + kwargs | list[ExtractedLearning] | LLM-powered extraction (optional) |

### CLI Commands

| Command | Description |
|---------|-------------|
| `dbnt process <text>` | Detect and route a protocol command |
| `dbnt detect <text>` | Classify a natural language signal |
| `dbnt score` | View scoring history |
| `dbnt success <pattern> -c <cat> -x <ctx>` | Encode a success rule |
| `dbnt failure <pattern> -c <cat> -x <ctx>` | Encode a failure rule |
| `dbnt learn <text> -d <domain> -i <importance>` | Record a learning |
| `dbnt patterns [--limit N]` | Detect recurring patterns |
| `dbnt promote [--limit N]` | Auto-promote qualifying patterns to rules |
| `dbnt sweep` | Run FSRS decay check |
| `dbnt dissonance` | Check success/failure balance |
| `dbnt status` | Full system overview |
| `dbnt rules` | List all rules with decay status |
| `dbnt show <rule_id>` | Show full rule content |
| `dbnt install --adapter <name>` | Install adapter (claude-code, generic) |
| `dbnt uninstall --adapter <name>` | Remove adapter |

### Adapter Interface

```python
class BaseAdapter(ABC):
    @abstractmethod def install(self) -> None: ...
    @abstractmethod def uninstall(self) -> None: ...
    @abstractmethod def get_rules_path(self) -> Path: ...
    @abstractmethod def sync_rule(self, rule: Rule) -> None: ...
    @abstractmethod def is_installed(self) -> bool: ...
```

Entry points registered in `pyproject.toml` under `[project.entry-points."dbnt.adapters"]`.

## Performance Requirements

| Operation | Target | Measured By |
|-----------|--------|------------|
| Command detection | <1ms | Regex match on short text |
| Signal detection | <1ms | Regex match on short text |
| Rule encoding | <10ms | File write to ~/.dbnt/ |
| Pattern detection (200 learnings) | <3s | SequenceMatcher pairwise |
| Pattern detection (500 learnings) | <15s | User-requested via --limit |
| Score state load/save | <5ms | JSON parse/serialize |
| Decay sweep (100 rules) | <100ms | SQLite reads + formula eval |

## Security Model

- **Authentication:** None. Local library, local state.
- **Authorization:** Filesystem permissions on `~/.dbnt/`. User-owned.
- **Data classification:** PUBLIC. No PII, no credentials, no sensitive data in rules.
- **Encryption:** None needed. Local files, no network transmission.
- **Network:** Zero outbound calls in core. Ollama extraction is opt-in and local (127.0.0.1:11434).

## Failure Modes

| Failure | Detection | Recovery |
|---------|-----------|----------|
| Corrupt score.json | JSONDecodeError on load | Fresh ScoreState (zero points, no events) |
| Corrupt learnings.db | sqlite3.Error on connect | Manual: delete and re-extract |
| Missing ~/.dbnt/ | Directory not found | Auto-created on first write |
| Ollama unavailable | URLError / TimeoutError | Fallback to regex extraction |
| O(n^2) timeout on large stores | User sees >3s delay | Auto-cap at 200 learnings, --limit flag |
| Contamination in learnings | System-prompt text stored | Contamination filter rejects known patterns |
| Rule file unparseable | parse_rule_file returns None | Skipped, other rules load normally |
