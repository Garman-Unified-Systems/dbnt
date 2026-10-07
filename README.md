# DBNT — Do Better Next Time

> Universal feedback protocol and learning system for AI agents. Turn corrections into persistent, weighted rules that survive across sessions.

[![Tests](https://github.com/Garman-Unified-Systems/dbnt/actions/workflows/ci.yml/badge.svg)](https://github.com/Garman-Unified-Systems/dbnt/actions)
[![PyPI version](https://badge.fury.io/py/dbnt.svg)](https://pypi.org/project/dbnt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Release status:** this source revision declares `0.6.0` as a release
candidate. The PyPI badge above reports the live published package; a source
version is not a publication claim. The DBNT x ABCD skill has its own release
rail and version.

---

## Quick Start

### Installation

**Python Package** (Python 3.10+ required):
```bash
pip install dbnt
```

**Development install** (requires Python 3.10+, use a venv if on a managed system):
```bash
git clone https://github.com/Garman-Unified-Systems/dbnt
cd dbnt
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

**Wire into Claude Code** (installs hooks to `~/.claude/hooks/`):
```bash
dbnt install --adapter claude-code
```

### 60-Second Example

```bash
# Your agent made a mistake. Signal it.
dbnt process "dbn"
# → Command: DBN | Action: encode_success | Response: "Yes Chef!"

# Check what signal natural language carries
dbnt detect "that's not quite right"
# → NEGATIVE | moderate | weight=0.8

dbnt detect "perfect, ship it"
# → POSITIVE | strong | weight=1.5

# Encode what worked
dbnt success "Use bun not npm" -c code -x "Project standard"

# Encode what failed
dbnt failure "Pushed directly to main" -c protocol -x "Always use feature branches"

# Report current decay categories (this does not move or delete files)
dbnt sweep

# Full system view
dbnt status
```

### Python API

```python
from dbnt import Protocol, detect_signal, encode_success

# Process a feedback command
protocol = Protocol()
response = protocol.process("dbnm")
# → Command: DBNM | Action: encode_success | "Yes Chef! Fixed, encoded, moving on."

# Classify a natural language signal
signal = detect_signal("that's not quite right")
# → SignalResult(polarity=NEGATIVE, strength=moderate, weight=0.8)

signal = detect_signal("perfect, ship it")
# → SignalResult(polarity=POSITIVE, strength=strong, weight=1.5)

# Record a success
encode_success(
    category="code",
    pattern="Used dataclass for config objects",
    context="Clean, typed, no dict key errors"
)
```

```python
from dbnt import LearningStore, PatternDetector, DecayEngine

store = LearningStore()
store.add("Always use timezone-aware datetimes", domain="code", importance=3)
store.add("Use timezone-aware datetime objects", domain="code", importance=2)
store.add("Always use UTC for datetime storage", domain="code", importance=4)

# Three similar learnings → pattern detected
detector = PatternDetector()
patterns = detector.detect(store.get_unpromoted())
# → [PatternGroup(count=3, confidence="low", should_promote=True)]

# Rules decay when unused, strengthen when applied
engine = DecayEngine(store)
engine.boost("rule_timezone_abc")       # Applied → stability increases
status = engine.check("rule_old_123")   # → {"status": "archive", "retrievability": 0.2}
```

---

## The Problem

Your AI agents make the same mistakes every session. You correct them, they improve — and then the context window resets and they're back to square one. Traditional memory systems record what went wrong, which creates agents that know a hundred ways to fail but can't reliably replicate success. DBNT encodes both sides of the feedback loop with information-theoretic weighting: success signals carry 1.5x weight because a working path is rarer and more valuable than a broken one.

---

## Why DBNT — The Structured Feedback Gap

The bottleneck in agentic AI isn't model capability. It's the feedback loop between human and AI.

Unstructured corrections — "that's wrong, try again" — don't transfer across sessions, don't distinguish severity, and don't accumulate into durable knowledge. The agent improves within a conversation, then resets. You correct the same mistake next week.

The failure mode compounds: AI agents generating plausible but unsupported output (hallucination) is a known and documented problem across every major provider. Even production-grade deep research tools carry rates that major providers have documented in their own evals. When the human correction loop is ad-hoc, these errors recur without accumulating toward resolution.

The missing piece is a structured protocol for human-to-AI correction signals. Not chat. Not thumbs-up/thumbs-down. A system that grades severity, distinguishes signal types, encodes learnings persistently, and weights success paths higher than failure paths.

That is what DBNT implements.

### Unstructured Feedback vs DBNT Protocol

| Dimension | Unstructured Feedback | DBNT Protocol |
|-----------|----------------------|---------------|
| Signal clarity | Ambiguous ("hmm, try again") | Explicit protocol commands plus natural-language signal classification |
| Persistence | Lost at session boundary | Encoded as rules, survives indefinitely |
| Success handling | Ignored or undifferentiated | Weighted 1.5x, separately tracked |
| Failure handling | Vague disapproval | Categorized; eligible learning groups promote only when an operator runs `dbnt promote` |
| Content fabrication defense | None | Corrections can be captured as durable local rules |
| Learning lifecycle | Accumulates without review | FSRS-inspired health classification and explicit boost operations |
| Multi-agent readiness | N/A | A shared filesystem root can be configured; synchronization is external |

Telling an AI "that's wrong" doesn't scale. Telling it *what severity of wrong*, encoding *what right looks like*, and managing those learnings over time — that scales.

---

## What DBNT Does

Five subsystems, one goal — agents that get better over time:

- **Protocol Engine** — Recognizes the explicit `db`, `dbn`, `dbnm`, `dbyc`, `fixed`, and `tweak` commands and records their score events.
- **Signal Detection** — Classifies common natural-language phrases by polarity, strength, and weight. The CLI reports the classification; callers decide whether to encode it.
- **Rule Encoding** — Stores learnings as human-readable markdown with weighted frontmatter. Success files and failure files, separately tracked
- **Learning System** — `dbnt patterns` reports similar learning groups. An eligible group becomes a rule only when an operator runs `dbnt promote`.
- **FSRS-inspired Decay Engine** — Explicit reviews and boosts update stability; `dbnt sweep` reports healthy, review, and archive candidates without moving files.

---

## Why Success Signals Outweigh Failure

Traditional approaches minimize loss. DBNT maximizes learning.

The intuition: there are infinite ways to fail a task, but only a handful of ways to do it well. A failure signal tells you one path to avoid out of infinite bad paths. A success signal tells you one path that works out of very few good paths — that's a higher information density per signal.

This is the **Ralph Wiggum Problem**: knowing 100 things not to do doesn't tell you what to do. Doctors study healthy patients. Athletes watch film of good plays. DBNT weights the game film accordingly.

> Failure: 1.0x weight — avoid this path
> Success: 1.5x weight — replicate this path

---

## The Learning Path

DBNT is designed for developers who've moved past basic AI chat. Here's how the capability layers stack:

### Level 1: Single Agent Feedback Loop

Wire DBNT into your AI tool and explicitly encode corrections worth retaining. DBNT persists those rules locally; your adapter or host application is responsible for loading relevant rules into later prompts.

- Install DBNT, run `dbnt install --adapter claude-code` (or `--adapter generic`)
- Use `dbnt detect` to classify natural-language feedback, then `dbnt success` or `dbnt failure` to persist the lesson
- In a later session, have your host read the rule files from the configured state directory

This gives the host a durable rule source; measuring whether repeat errors fall remains the host's responsibility.

### Level 2: Persistent Rules with Lifecycle Management

Rules accumulate. Without review, you can end up with stale files that slow context loading and contradict each other. DBNT supplies decay state and a classification report; the operator controls archival.

- Explicit `DecayEngine.boost` calls increase stability
- Reviewed rules change stability; `dbnt sweep` reports candidates but does not archive them
- `dbnt dissonance` reports aggregate success/failure balance; it does not compare rule content or detect conflicts

The report gives an operator or host application evidence to review or archive rules. DBNT 0.6.0 does not mutate rule files during a sweep.

### Level 3: Explicit Pattern Promotion

When the learning store contains three or more similar entries, `dbnt patterns` can report the eligible group. A rule is written only when an operator runs `dbnt promote`.

- `dbnt patterns` groups similar entries when invoked
- `dbnt promote` applies the 3+ occurrence threshold and writes qualifying rules
- The CLI creates and promotes rules; skill versioning and rollback are outside the package

Promotion is explicit and operator-triggered; DBNT does not claim that the resulting rule is automatically loaded or changes agent behavior.

### Level 4: Multi-Agent Coordination (The Horizon)

DBNT can point multiple processes at the same `DBNT_DIR`, but 0.6.0 provides no transport, replication, locking protocol, cross-node propagation, or peer-review mechanism. Hosts that share a store must supply those operational controls.

Multi-agent and cross-node propagation remain roadmap work rather than a 0.6.0 package capability.

Level 4 is a possible integration direction. Treat the local filesystem and API in this release as building blocks, not as a distributed coordination system.

---

## Bring Your Own Everything

### Bring Your Own Model

DBNT doesn't call any LLM APIs. It processes feedback signals and manages rule storage. Your model choice is completely orthogonal. Run it with Claude, GPT-4, Ollama, LM Studio, llama.cpp — anything that generates text and can receive context injection.

If you want transcript-based signal extraction (parsing conversation history for implicit feedback), that processing happens on your stack with your model.

### Bring Your Own Tools

Adapters connect DBNT to host tooling. The Claude Code adapter installs `UserPromptSubmit` and `Stop` hooks for score tracking and transcript extraction. The generic adapter creates the state directories and exposes rule synchronization methods; it does not run a filesystem watcher.

```bash
dbnt install --adapter claude-code    # Hooks/rule mirror in ~/.claude; state in $DBNT_DIR
dbnt install --adapter generic         # Initializes $DBNT_DIR/rules/
```

### Bring Your Own Keys

DBNT has no API keys, no cloud dependencies, no telemetry. Everything runs locally. The rule store is a directory of markdown files. The learning store is a SQLite file. The score history is JSON. You own all of it.

---

## Protocol Commands

The escalation ladder — each level signals increasing severity and triggers different encoding behavior:

| Command | Meaning | Points | Agent Response |
|---------|---------|--------|----------------|
| `db` | Do Better — recoverable mistake | −1 | Fix it + encode the success pattern |
| `dbn` | Do Better Now — same class of mistake | −1 | Fix it faster + encode |
| `dbnm` | Do Better Now Move — fix it and keep going | −1 | Fix + encode + don't stop to discuss |
| `dbyc` | Critical — you had to take over | −2 | Encode BOTH the failure AND what worked |
| `good` / `fixed` / `ship it` | Confirmed working | +3 | Acknowledge (1.5x weighted) |
| `tweak` | Close, iterate | +0.5 → −1 | Degrades on repetition |

The protocol response text uses **"Yes Chef!"** and returns an action such as `encode_success` or `encode_both`. The caller remains responsible for performing the fix and invoking the encoding operation.

`dbyc` returns `encode_both` because a takeover contains two useful learnings: what the agent did wrong and what the human did right. A host can use that action to persist both.

---

## Signal Detection

DBNT classifies feedback from natural language, so you don't need to remember commands in the moment. Common signal mappings:

| Natural Language | Signal | Weight |
|-----------------|--------|--------|
| "perfect", "ship it", "exactly right" | POSITIVE_STRONG | 1.5x |
| "good", "that works", "correct" | POSITIVE_MODERATE | 1.2x |
| "not quite", "close but", "almost" | NEGATIVE_MODERATE | 0.8x |
| "wrong", "that's broken", "no" | NEGATIVE_STRONG | 1.0x (encode failure) |
| "i had to fix this myself" | CRITICAL | 2.0x (encode both) |

No event is recorded for silence. Neutral phrases are classified when they are explicitly passed to the signal detector.

---

## State Directory

All DBNT state uses one root. It defaults to `~/.dbnt/`; set `DBNT_DIR` to a non-empty path for project-local or externally managed storage:

```
~/.dbnt/
├── rules/
│   ├── successes/     # What worked — 1.5x weighted
│   ├── failures/      # What failed — 1.0x weighted
├── learnings.db       # SQLite — pattern detection, decay tracking
└── score.json         # Running score history
```

The state directory is portable as a unit. `DBNT_DIR` is read by the CLI, Python stores, protocol engine, adapters, and generated hooks. Explicit Python constructor paths take precedence over the environment.

A rule created by `dbnt success` looks like this:

```markdown
# Success: Used timezone-aware datetimes

**Category**: code
**Weight**: 1.5
**Created**: 2026-08-16
**Source**: unknown

## Context

Project stores timestamps across time zones.

## Pattern

Use timezone-aware datetime objects. Store in UTC, display in local time.

## When to Apply

[Auto-generated - edit as needed]
```

Human-readable. Diffable. Version-controllable if you want.

---

## Capture → Compound → Mine — GUSystems Skill Pack #1

The repository includes a source-tree reference skill under `skills/dbnt-feedback/`. It is instruction content for compatible agent hosts, not part of the PyPI wheel and not an automatic extension of the CLI. A separately versioned public skill is being prepared in [garman-skills](https://github.com/idirectships/garman-skills); install and release it independently.

The DBNT feedback loop has three phases beyond individual rule capture:

### Phase 1: Capture

In the reference skill, capture mode instructs the host agent to turn a correction or explicit rule request into a markdown artifact under `$DBNT_DIR/rules/successes/` or `failures/`. The package's `dbnt process` command returns an encode action; it does not write a rule until the caller or operator invokes the encoding API/CLI.

`DBNT_DIR` defaults to `~/.dbnt/`. Override for per-project isolation:

```bash
DBNT_DIR=./dbnt dbnt success "Used typed dataclass for config" -c code
```

### Phase 2: Compound

The package's `dbnt patterns` command groups similar unpromoted rows in `learnings.db`; `dbnt promote` turns groups of three or more into ordinary success or failure rule files. The richer "compound" workflow described by the reference skill is agent instruction content, not a CLI command.

### Phase 3: Mine

The reference skill describes a human/agent-guided root-cause review. DBNT 0.6.0 has no `mine` CLI command or canonical-class report.

### The ABCD disposition check

ABCD disposition is defined by the separately versioned skill. It is not evaluated or written automatically by the Python package.

---

### Claude Code skill

The source-tree reference and the separately versioned skill may instruct an agent to use DBNT artifacts, but neither is bundled in `pip install dbnt`. The package owns the CLI, Python API, state layout, scoring, pattern grouping, promotion, and decay classification. The skill owns agent-facing routing and disposition instructions.

---

## FSRS-6 Decay

Rules use the FSRS retrievability formula:

```
R(t, S) = (1 + t / (9 × S))^(-1)
```

Where `t` = days since the recorded review and `S` = stability. An explicit boost increases stability. New rules without a decay review remain healthy; this release does not infer applications from rule-file access.

`dbnt sweep` classifies rule IDs and prints candidates. It never deletes, moves, or archives rule files.

---

## CLI Reference

```bash
# Protocol
dbnt process "dbnm"              # Detect and route a command
dbnt score                        # View scoring history

# Signals
dbnt detect "that's perfect"      # Classify a signal

# Rules
dbnt success "Use bun not npm" -c code -x "Project standard"
dbnt failure "Pushed to main" -c protocol -x "Always use feature branches"

# Learning
dbnt learn "Always validate at boundaries" -d code -i 3
dbnt patterns                     # Show recurring patterns (caps at 200 learnings)
dbnt patterns --limit 500         # Scan more learnings (slower on large stores)
dbnt promote                      # Auto-promote qualifying patterns to rules
dbnt sweep                        # Report FSRS-inspired decay categories

# Status
dbnt status                       # Full system overview
dbnt dissonance                   # Surface conflicting success/failure signals

# Claude Code integration
dbnt install --adapter claude-code    # Wire hooks to ~/.claude/hooks/
dbnt uninstall                         # Remove hooks
```

### Performance Note

`dbnt patterns` uses O(n²) SequenceMatcher to group similar learnings. On stores with 500+ learnings, it caps automatically (default 200) to stay under ~3 seconds. Use `--limit` to scan more at the cost of time.

---

## Adapters and Integrations

| Adapter | Status | Description |
|---------|--------|-------------|
| Claude Code | Beta | Installs hooks, keeps the existing `~/.claude/rules` sync target, and stores score/learnings under `$DBNT_DIR`; no rule injection |
| Generic | Stable | Creates directories and provides file-based rule synchronization methods |
| LangChain | Planned | Callback handler on chain completion |
| CrewAI | Planned | Task completion hook |
| AutoGen | Planned | Agent feedback loop integration |
| Cursor | Planned | `.cursorrules` injection |
| MCP Server | Planned | Model Context Protocol adapter |

---

## Architecture

```
Human feedback
    │
    ├─ "dbnm" ────────► Protocol Engine ──► Score tracking + encode action
    ├─ "perfect" ─────► Signal Detector ──► POSITIVE (1.5x weight)
    └─ "not quite" ───► Signal Detector ──► NEGATIVE (1.0x weight)
                                │
                                ▼
                     Rule files (markdown)
                                │
                                ▼
                    Learning Store (SQLite)
                                │
                                ▼
                     Pattern Detector
                     (3+ similar → promote)
                                │
                                ▼
                    FSRS-6 Decay Engine
                    ├─ Applied? ──► Boost stability
                    └─ Sweep ─────► Report review/archive candidates
```

No middleware, cloud calls, or telemetry. Signals and protocol commands produce structured results; explicit encode operations persist rules.

---

## Comparison

| Feature | DBNT | Traditional Logging | Vector Memory |
|---------|------|-------------------|---------------|
| Persists across sessions | Yes | No | Partial |
| Success/failure weighting | 1.5x / 1.0x | Equal | N/A |
| Human-readable rules | Markdown | Logs | Vectors |
| Decay / lifecycle | FSRS-6 | Manual | None |
| LLM-agnostic | Yes | Yes | Usually not |
| Local-first | Yes | Varies | Usually cloud |
| Zero cloud dependencies | Yes | Varies | Heavy |
| Pattern auto-promotion | Yes, from learning rows | No | No |
| Distributed propagation | No | No | Varies |

---

## Contributing

Issues, PRs, and discussion welcome on [GitHub](https://github.com/Garman-Unified-Systems/dbnt).

What we accept without prior discussion:
- New adapter implementations
- Signal detection improvements and edge cases
- Test coverage additions
- Documentation fixes

What needs a discussion issue first:
- Changes to the core protocol command set
- Modifications to the FSRS decay parameters
- New storage backends

---

## License

MIT

---

## What's Next

DBNT 0.6.0 is a local feedback and rule-lifecycle toolkit. Distributed propagation, skill versioning, rollback, automatic rule injection, and autonomous archival remain outside this release. Start with one state root, measure the correction loop, and add host integration deliberately.

---

*Built by [Drew Garman](https://github.com/idirectships). MIT licensed.*
