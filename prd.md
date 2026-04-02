# PRD -- DBNT

> Notion: https://www.notion.so/331b18c770b28132bf6cf16521a2f4f5

## Vision

A universal feedback protocol that makes AI agents learn from human corrections across sessions, turning ad-hoc "that's wrong" moments into persistent, weighted rules with lifecycle management.

## Users

1. **AI agent developers** building systems that interact with humans and need to stop repeating mistakes. They wire DBNT into their agent's feedback loop (Claude Code, LangChain, custom). They care about: persistent memory, zero cloud dependencies, easy integration.

2. **AI power users** running tools like Claude Code daily who are tired of correcting the same behavior every session. They install via `pip install dbnt` + `dbnt install --adapter claude-code`. They care about: it just works, corrections stick, no configuration.

3. **Multi-agent system builders** orchestrating multiple AI agents that need shared learning. They use DBNT's rule store as a swarm memory layer. They care about: cross-agent propagation, rule lifecycle, dissonance monitoring.

## Success Criteria

| Metric | Target | How Measured |
|--------|--------|-------------|
| Repeat correction rate | <5% after 2 weeks of use | Same pattern encoded twice = repeat |
| Rule store health | >60% success rules (weighted) | `dbnt dissonance` output |
| Time to first value | <2 minutes | Install -> first rule encoded |
| Stale rule ratio | <20% of active rules | `dbnt sweep` archive count vs total |
| PyPI installs | Growth month-over-month | PyPI download stats |

## Features

### FEAT-001: Protocol Engine
**Priority:** P0
**Status:** Complete (v0.2.0)

As an AI agent, I receive structured correction commands (DB/DBN/DBNM/DBYC) so that I know the severity of my mistake and what action to take.

**Acceptance criteria:**
- [x] Detect DB, DBN, DBNM, DBYC commands from text
- [x] Route to correct action (encode_success, encode_both, iterate, acknowledge)
- [x] Track score with point system (-1, -2, +2, +0.5)
- [x] Persist score state to disk
- [x] Tweak degradation (first +0.5, subsequent -1 each)

### FEAT-002: Signal Detection
**Priority:** P0
**Status:** Complete (v0.2.0)

As a human, I can give natural language feedback ("not quite", "perfect") without remembering protocol commands, and the system classifies my intent.

**Acceptance criteria:**
- [x] Classify positive strong/moderate, negative strong/moderate, neutral
- [x] Weight signals: success 1.5x, failure 1.0x
- [x] Regex-based, no external dependencies
- [x] Case-insensitive matching

### FEAT-003: Rule Encoding
**Priority:** P0
**Status:** Complete (v0.2.0)

As an AI agent, my learnings are stored as human-readable markdown files with weighted frontmatter, separated by success/failure.

**Acceptance criteria:**
- [x] Success rules at 1.5x weight, failure at 1.0x
- [x] 10 categories: format, code, explain, tool, comm, protocol, preference, waste, gap, integration
- [x] Markdown with structured sections (Context, Pattern, When to Apply)
- [x] Collision-resistant IDs (timestamp + random hex)

### FEAT-004: FSRS-6 Decay Engine
**Priority:** P0
**Status:** Complete (v0.5.0)

As a system, rules that get applied grow stronger and rules that sit unused fade toward archival, keeping the rule store lean.

**Acceptance criteria:**
- [x] Retrievability formula: R(t,S) = (1 + t/(9*S))^(-1)
- [x] Boost on application (rating=3)
- [x] Sweep categorizes rules as healthy/review/archive
- [x] Archive threshold at 0.3 retrievability
- [x] Stability and difficulty tracking per rule

### FEAT-005: Pattern Detection + Auto-Promotion
**Priority:** P1
**Status:** Complete (v0.5.0)

As a system, when the same class of correction appears 3+ times, the pattern auto-promotes to a permanent rule.

**Acceptance criteria:**
- [x] SequenceMatcher grouping at 0.7 similarity threshold
- [x] 3+ occurrences triggers promotion
- [x] Promoted learnings marked in SQLite
- [x] Confidence tiers: low (<5), medium (5-9), high (10+)
- [x] O(n^2) capped at 200 learnings by default

### FEAT-006: Transcript Extraction
**Priority:** P1
**Status:** Complete (v0.5.0)

As a system, I can parse session transcripts (JSONL or plain text) and extract learnings without manual tagging.

**Acceptance criteria:**
- [x] Regex-based extraction (zero dependencies)
- [x] Optional Ollama-powered extraction (local LLM)
- [x] JSONL transcript formatting with 20/80 truncation
- [x] Contamination filter (rejects system-prompt noise)
- [x] Dedup on first 80 normalized chars

### FEAT-007: Adapter System
**Priority:** P1
**Status:** Complete (v0.5.0)

As a developer, I can integrate DBNT into any AI tool through a plugin adapter interface.

**Acceptance criteria:**
- [x] BaseAdapter ABC (5 methods: install, uninstall, sync_rule, get_rules_path, is_installed)
- [x] Claude Code adapter (hooks UserPromptSubmit + Stop)
- [x] Generic file-based adapter
- [x] Entry point registration in pyproject.toml
- [ ] LangChain adapter (planned)
- [ ] Cursor adapter (planned)
- [ ] MCP Server adapter (planned)

### FEAT-008: Dissonance Monitor
**Priority:** P2
**Status:** Complete (v0.2.0)

As a user, I can check if my rule store is anxiety-driven (too many failure rules) or balanced.

**Acceptance criteria:**
- [x] Target: 60% weighted success rules
- [x] Dissonance = |target - actual| success rate
- [x] Status tiers: balanced, slight_imbalance, moderate_imbalance, severe_imbalance
- [x] Actionable recommendations

## Out of Scope

- **RAG / vector search** -- DBNT is rule-based, not retrieval-based. Use a vector DB for that.
- **Chat history / context windows** -- DBNT encodes learnings, not conversations.
- **Model fine-tuning** -- DBNT operates at the prompt/context layer, not the weights layer.
- **Cloud services** -- local-first is non-negotiable. No hosted version planned.
- **Prompt templates** -- DBNT is for runtime learning, not static prompt engineering.

## Timeline

| Milestone | Date | Deliverable |
|-----------|------|-------------|
| v0.1.0 | 2026-01-06 | Core protocol, signal detection, CLI |
| v0.2.0 | 2026-01-06 | Adapters, dissonance, rule categories |
| v0.5.0 | 2026-03-15 | FSRS decay, pattern promotion, transcript extraction, CI |
| v0.5.2 | 2026-03-20 | Performance cap, dedup, contamination filter |
| v0.6.0 | TBD | LangChain adapter, MCP server adapter |
| v1.0.0 | TBD | Stable API, multi-agent rule propagation |
