# Architecture -- DBNT

> Notion: https://www.notion.so/331b18c770b281f990b8c767e204990e

## Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Runtime | Python 3.10+ | Broad ecosystem, stdlib-rich (sqlite3, re, pathlib, dataclasses) |
| CLI | click >=8.0 | Only runtime dependency. Declarative, composable, well-tested |
| Storage | Markdown files + SQLite | Human-readable rules + structured learning data. Zero server deps |
| Build | hatchling | Modern PEP 517 backend, minimal config |
| CI | GitHub Actions | Python 3.10-3.13 matrix on ubuntu-latest |
| Registry | PyPI | `pip install dbnt` |

## System Map

```
Human Feedback
    |
    +-- "dbnm" ---------> Protocol Engine -----> Score tracking + encode action
    +-- "perfect" -------> Signal Detector -----> POSITIVE (1.5x weight)
    +-- "not quite" -----> Signal Detector -----> NEGATIVE (1.0x weight)
    +-- transcript JSONL -> Extract Engine ------> Regex or Ollama extraction
                                |
                                v
                     Rule files (markdown)    ~/.dbnt/rules/{successes,failures}/*.md
                                |
                                v
                    Learning Store (SQLite)   ~/.dbnt/learnings.db
                                |
                                v
                     Pattern Detector         SequenceMatcher grouping (0.7 threshold)
                     (3+ similar -> promote)
                                |
                                v
                    FSRS-6 Decay Engine       R(t,S) = (1 + t/(9*S))^(-1)
                    +-- Applied? --> Boost stability
                    +-- Unused?  --> Fade -> archive
```

## Patterns

- **State management:** ScoreState persisted as JSON (`~/.dbnt/score.json`). Learning state in SQLite. Rule files as individual markdown.
- **Data flow:** Unidirectional. Input -> detection -> encoding -> storage -> decay. No cycles.
- **Error handling:** Graceful fallbacks everywhere. Ollama down -> regex extraction. Corrupt JSON -> fresh ScoreState. Missing dirs -> auto-create.
- **Dedup:** Cross-session and within-session dedup on first 80 normalized chars. Contamination filter rejects system-prompt noise.
- **Adapter pattern:** `BaseAdapter` ABC with 5 methods. New integrations implement the interface without touching core.

## Dependencies

| Package | Version | Purpose | Required |
|---------|---------|---------|----------|
| click | >=8.0 | CLI framework | Yes (runtime) |
| pytest | >=7.0 | Testing | Dev only |
| pytest-cov | >=4.0 | Coverage | Dev only |
| ruff | >=0.1.0 | Linting + formatting | Dev only |
| mypy | >=1.0 | Type checking (strict) | Dev only |
| langchain-core | >=0.1.0 | LangChain adapter | Optional (`dbnt[langchain]`) |

Zero runtime dependencies beyond click. Everything else is Python stdlib: `sqlite3`, `pathlib`, `dataclasses`, `re`, `json`, `secrets`, `difflib`, `enum`, `datetime`, `urllib`.

## Infrastructure

- **Hosting:** PyPI (`pip install dbnt`). Source on GitHub (idirectships/dbnt).
- **CI/CD:** GitHub Actions. Triggered on push to main + PRs to main. Matrix: Python 3.10, 3.11, 3.12, 3.13. Steps: lint (ruff) -> test (pytest).
- **Plugin packaging:** `.claude-plugin/` directory for Claude Code marketplace distribution.
- **Monitoring:** None (local-first library, not a service).

## Module Dependency Graph

```
cli.py
  +-- protocol.py       (Command, Action, Protocol, ProtocolResponse)
  +-- core.py            (encode_success, encode_failure, check_dissonance, RuleStore)
  +-- learning.py        (LearningStore, PatternDetector, DecayEngine)
  +-- signals/detector.py (detect_signal)
  +-- adapters/claude_code.py
  +-- adapters/generic.py

core.py
  +-- storage/rules.py   (load_rules_from_dir, parse_rule_file)

extract.py               (standalone -- no internal deps beyond stdlib)
learning.py              (standalone -- no internal deps beyond stdlib)
signals/detector.py      (standalone -- no internal deps beyond stdlib)
adapters/base.py         (imports core.Rule only)
```

## Local State Layout

```
~/.dbnt/
+-- rules/
|   +-- successes/       # Markdown rule files (1.5x weighted)
|   +-- failures/        # Markdown rule files (1.0x weighted)
|   +-- patterns/        # Auto-promoted from recurring learnings
+-- learnings.db         # SQLite: learnings table + rule_decay table
+-- score.json           # Protocol score history (JSON)
```

## Constraints

- **Performance:** Pattern detection is O(n^2) via SequenceMatcher. Capped at 200 learnings by default. `--limit` flag for manual override.
- **Security:** Zero network calls in core library. Ollama extraction is opt-in and local-only. No API keys, no telemetry, no cloud. State directory is user-owned (`~/.dbnt/`).
- **Cost:** $0. No cloud services. No API keys. No subscriptions.
- **Compatibility:** Python 3.10+ (uses `X | Y` union syntax). Tested on 3.10-3.13.
