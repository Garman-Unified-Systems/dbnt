# DBNT — Do Better Next Time

> Universal feedback protocol and learning system for AI agents. Turn corrections into persistent, weighted rules that survive across sessions.

[![Tests](https://github.com/idirectships/dbnt/actions/workflows/ci.yml/badge.svg)](https://github.com/idirectships/dbnt/actions)
[![PyPI version](https://badge.fury.io/py/dbnt.svg)](https://pypi.org/project/dbnt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

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
| Signal clarity | Ambiguous ("hmm, try again") | Severity-graded (DB/DBN/DBNM/DBYC) |
| Persistence | Lost at session boundary | Encoded as rules, survives indefinitely |
| Success handling | Ignored or undifferentiated | Weighted 1.5x, separately tracked |
| Failure handling | Vague disapproval | Categorized, pattern-detected, auto-promoted |
| Content fabrication defense | None | Signal detection catches drift; corrections encode immediately |
| Learning lifecycle | Accumulates without pruning | FSRS-6 decay — stale rules archive, active rules strengthen |
| Multi-agent readiness | N/A | Shared rule stores, cross-agent propagation |

Telling an AI "that's wrong" doesn't scale. Telling it *what severity of wrong*, encoding *what right looks like*, and managing those learnings over time — that scales.

---

## What DBNT Does

Six subsystems, one goal — agents that get better over time:

- **Protocol Engine** — Escalating correction commands (DB → DBN → DBNM → DBYC) with point scoring and structured action routing
- **Signal Detection** — Classifies natural language feedback without requiring special syntax. "That's not quite right" is as valid as `dbn`
- **Rule Encoding** — Stores learnings as human-readable markdown with weighted frontmatter. Success files and failure files, separately tracked
- **Learning System** — Pattern detection groups similar corrections. Three occurrences of the same pattern auto-promotes it to a permanent rule
- **FSRS Decay Engine** — Rules that get applied grow stronger. Rules that sit unused fade toward archival. Based on the [FSRS-6 spaced-repetition algorithm](https://github.com/open-spaced-repetition/py-fsrs)
- **Bounded Agency Policy** — Deterministically classifies a proposed next step as MOVE, GATE, or DROP so correction produces forward motion instead of overstep/passivity oscillation

---

## Why Success Signals Outweigh Failure

Traditional approaches minimize loss. DBNT maximizes learning.

The intuition: there are infinite ways to fail a task, but only a handful of ways to do it well. A failure signal tells you one path to avoid out of infinite bad paths. A success signal tells you one path that works out of very few good paths — that's a higher information density per signal.

This is the **Ralph Wiggum Problem**: knowing 100 things not to do doesn't tell you what to do. Doctors study healthy patients. Athletes watch film of good plays. DBNT weights the game film accordingly.

> Failure: 1.0x weight — avoid this path
> Success: 1.5x weight — replicate this path

---

## Quick Start

### Installation

**Python Package** (Python 3.10+ required):
```bash
pip install dbnt
```

**Development install** (requires Python 3.10+, use a venv if on a managed system):
```bash
git clone https://github.com/idirectships/dbnt
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

# Run the decay sweep — archives stale rules, boosts active ones
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

### Bounded Agency API

Feedback is useful only if it improves the next action. DBNT's bounded-agency
policy operates on structured runtime facts rather than guessing intent from
natural language:

```python
from dbnt import ActionProposal, Effect, classify_action

decision = classify_action(
    ActionProposal(
        name="apply the tested local fix",
        advances_outcome=True,
        effect=Effect.LOCAL_MUTATION,
    )
)
assert decision.disposition.value == "move"

external = classify_action(
    ActionProposal(
        name="publish without approval",
        advances_outcome=True,
        effect=Effect.EXTERNAL_MUTATION,
    )
)
assert external.disposition.value == "gate"
```

The policy uses one invariant: **advance the goal with the smallest bounded
move; gate only on a real unsatisfied boundary.**

- **MOVE** — in-scope action or live-state evidence may proceed
- **GATE** — scope, current-state, external, irreversible, credential, privacy,
  or authority requirements remain unsatisfied
- **DROP** — narration or ceremony produces neither a state change nor
  decision-grade evidence

Run the built-in regression suite with `dbnt agency-check`. It covers safe
bounded fixes, live-state verification, duplicate permission requests, passive
stopping after correction, stale sealed transactions, and unauthorized external
mutation.

`effect` is required. External effects automatically derive both the external
and authority boundaries, and irreversible effects derive the irreversible and
authority boundaries. A caller cannot turn an external action into MOVE merely
by omitting those boundary labels or by self-declaring boundary grants;
`authority_verified=True` is a separate required fact.

Runtime adapters can enforce the decision before invoking a callback:

```python
from dbnt import ActionProposal, Effect
from dbnt.adapters.generic import GenericAdapter

adapter = GenericAdapter()
proposal = ActionProposal(
    name="apply tested fix",
    advances_outcome=True,
    effect=Effect.LOCAL_MUTATION,
)
result = adapter.run_action(proposal, lambda: "done")  # raises unless MOVE
```

For process boundaries, `dbnt agency-decide` classifies one supplied action as
JSON and exits `0` only for MOVE (`2` for GATE, `3` for DROP):

```bash
dbnt agency-decide --name publish --effect external_mutation
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

## The Learning Path

DBNT is designed for developers who've moved past basic AI chat. Here's how the capability layers stack:

### Level 1: Single Agent Feedback Loop

Wire DBNT into your AI tool. Every mistake your agent makes, every correction you give, gets encoded as a rule. The next session, that rule is injected back into context. The agent stops repeating itself.

- Install DBNT, run `dbnt install --adapter claude-code` (or `--adapter generic`)
- Agent makes a mistake → you say "not quite" → signal detected → rule encoded
- Next session: rule is loaded, mistake doesn't recur

This alone significantly reduces repeat errors by making every failure a teachable moment the agent encodes immediately.

### Level 2: Persistent Rules with Lifecycle Management

Rules accumulate. Without management, you end up with hundreds of stale files that slow context loading and contradict each other. FSRS-6 handles this automatically.

- Frequently-applied rules gain stability — they're harder to decay
- Unused rules fade — `dbnt sweep` archives them
- `dbnt dissonance` surfaces conflicting rules before they cause issues

The rule store stays lean. Only actively relevant rules survive.

### Level 3: Skill Improvement Through Pattern Promotion

When you correct the same class of mistake three or more times, DBNT detects the pattern and auto-promotes it to a permanent, high-confidence rule. Individual learnings become structural improvements.

- Similar corrections cluster automatically
- Promotion threshold: 3+ occurrences with pattern confidence
- Skills versioned: `code-review v1 → v2 → v3`
- Rollback available if a new version performs worse

Your agent's behavior across a domain improves without manual rule-writing.

### Level 4: Multi-Agent Coordination (The Horizon)

This is where DBNT becomes a swarm memory layer. The protocol and storage architecture already support it — shared rule stores, cross-agent learning propagation, probabilistic peer review between agents.

Agent A learns something. Agent B gets that learning without making the mistake itself. Agents critique each other's outputs. The swarm's collective rule base evolves.

Level 4 is where this framework is heading. We run a production system across multiple nodes that uses DBNT as its learning substrate — agents coordinating autonomously, rules propagating across the network, skills compounding over time. The implementation details of that system aren't open source, but the foundation you'd build it on is exactly this.

---

## Bring Your Own Everything

### Bring Your Own Model

DBNT doesn't call any LLM APIs. It processes feedback signals and manages rule storage. Your model choice is completely orthogonal. Run it with Claude, GPT-4, Ollama, LM Studio, llama.cpp — anything that generates text and can receive context injection.

If you want transcript-based signal extraction (parsing conversation history for implicit feedback), that processing happens on your stack with your model.

### Bring Your Own Tools

Adapters connect DBNT to whatever AI tooling you use. The Claude Code adapter hooks `UserPromptSubmit` and `Stop` events. The generic adapter uses filesystem watching and markdown files — it works with anything. Adding your own adapter is around 50 lines implementing a simple interface.

```bash
dbnt install --adapter claude-code    # Installs to ~/.claude/hooks/ and ~/.claude/rules/
dbnt install --adapter generic         # Installs to ~/.dbnt/rules/
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
| `tweak` / `almost` | Close, iterate | +0.5 → −1 | Degrades on repetition |

The required response to any correction command is **"Yes Chef!"** — then fix, encode, continue. The kitchen protocol framing is intentional: corrections are instructions, not critiques.

`dbyc` is the most important signal. When a human has to step in and finish the work themselves, there are two learnings to capture: what the agent did wrong, and what the human did right. Both get encoded.

---

## Signal Detection

DBNT classifies feedback from natural language, so you don't need to remember commands in the moment. Common signal mappings:

| Natural Language | Signal | Weight |
|-----------------|--------|--------|
| "perfect", "ship it", "exactly right" | POSITIVE_STRONG | 1.5x |
| "good", "that works", "correct" | POSITIVE_MODERATE | 1.2x |
| "ok", "sure", "fine" | NEUTRAL | 1.0x |
| "not quite", "close but", "almost" | NEGATIVE_MODERATE | 0.8x |
| "wrong", "that's broken", "no" | NEGATIVE_STRONG | 1.0x (encode failure) |
| "i had to fix this myself" | CRITICAL | 2.0x (encode both) |

Silence is treated as neutral approval. The system doesn't require active positive feedback to function — only corrections.

---

## State Directory

All DBNT state lives in `~/.dbnt/`:

```
~/.dbnt/
├── rules/
│   ├── successes/     # What worked — 1.5x weighted
│   ├── failures/      # What failed — 1.0x weighted
│   └── patterns/      # Auto-promoted from recurring learnings
├── learnings.db       # SQLite — pattern detection, decay tracking
└── score.json         # Running score history
```

The `~/.dbnt/` directory is portable. Copy it to a new machine, run `dbnt status`, and the full history is there.

A rule file looks like this:

```markdown
---
id: rule_timezone_2024_abc1
category: code
weight: 1.5
stability: 4.2
retrievability: 0.87
created: 2024-11-03
last_applied: 2024-11-14
---

# Always Use Timezone-Aware Datetimes

Always use timezone-aware datetime objects. Store in UTC, display in local time.

## Context
Three separate corrections on datetime handling across different projects.
Auto-promoted from pattern after 3+ occurrences.
```

Human-readable. Diffable. Version-controllable if you want.

---

## FSRS-6 Decay

Rules use the FSRS retrievability formula:

```
R(t, S) = (1 + t / (9 × S))^(-1)
```

Where `t` = days since last application, `S` = stability score. Apply a rule → stability increases, slower decay. Ignore a rule → retrievability drops toward the archival threshold.

This prevents the rule store from bloating with stale context that hurts more than it helps.

---

## CLI Reference

```bash
# Protocol
dbnt process "dbnm"              # Detect and route a command
dbnt score                        # View scoring history
dbnt agency-check                 # Verify MOVE/GATE/DROP policy regressions
dbnt agency-decide --name inspect --effect observe --evidence
                                  # Enforce one runtime action decision

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
dbnt sweep                        # Run FSRS decay check — archives stale rules

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
| Claude Code | Stable | Hooks `UserPromptSubmit` + `Stop`, injects rules into context |
| Generic | Stable | File-based, filesystem events — works with any tool |
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
                    └─ Unused?  ──► Fade → archive
```

No middleware. No cloud calls. The signal goes in, the rule comes out, the agent gets better.

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
| Pattern auto-promotion | Yes | No | No |
| Multi-agent ready | Yes (shared store) | No | Partial |

---

## Contributing

Issues, PRs, and discussion welcome on [GitHub](https://github.com/idirectships/dbnt).

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

DBNT is a foundation layer, not a finished product. A single agent with persistent memory is useful. An agent whose skills compound over weeks of corrections is more useful. A network of agents sharing a rule store and improving collectively is something else entirely.

We run a production system built on this foundation — multiple nodes coordinating autonomously, rules propagating across agents, skills versioning and rolling back based on performance signals. That system isn't open source. But the protocol it runs on is exactly what you're installing.

Start at Level 1. Wire it into your current setup. Watch the correction rate drop over a few weeks. Then decide how far you want to take it.

---

*Built by [Dru Garman](https://github.com/idirectships). MIT licensed.*
