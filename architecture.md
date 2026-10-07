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
                     Rule files (markdown)    $DBNT_DIR/rules/{successes,failures}/*.md
                                |
                                v
                    Learning Store (SQLite)   $DBNT_DIR/learnings.db
                                |
                                v
                     Pattern Detector         SequenceMatcher grouping (0.7 threshold)
                     (3+ similar -> promote)
                                |
                                v
                    FSRS-6 Decay Engine       R(t,S) = (1 + t/(9*S))^(-1)
                    +-- Applied? --> Boost stability
                    +-- Sweep --------> Report review/archive candidates
```

## Patterns

- **State management:** One resolver selects `DBNT_DIR` or the `~/.dbnt` default. ScoreState is JSON, learning/decay state is SQLite, and rules are markdown files.
- **Data flow:** Unidirectional. Input -> detection -> encoding -> storage -> decay. No cycles.
- **Error handling:** Ollama extraction can fall back to regex. Corrupt score JSON is quarantined before a clean ScoreState is used. Missing state directories are created on write.
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
| build | >=1.2 | Wheel/sdist release gate | Dev only |
| twine | >=5.0 | Distribution metadata check | Dev only |
| langchain-core | >=0.1.0 | LangChain adapter | Optional (`dbnt[langchain]`) |

Zero runtime dependencies beyond click. Everything else is Python stdlib: `sqlite3`, `pathlib`, `dataclasses`, `re`, `json`, `secrets`, `difflib`, `enum`, `datetime`, `urllib`.

## Infrastructure

- **Hosting:** PyPI (`pip install dbnt`). Source on GitHub ([Garman-Unified-Systems/dbnt](https://github.com/Garman-Unified-Systems/dbnt)).
- **CI/CD:** GitHub Actions. PR/main CI covers Python 3.10-3.13. Tag-only publication requires an exact package-matching `vX.Y.Z` tag on a main ancestor, green tests/lint, build, and `twine check` before OIDC publication.
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

state.py                 (single DBNT_DIR/default resolver)

core.py
  +-- storage/rules.py   (load_rules_from_dir, parse_rule_file)

extract.py               (standalone -- no internal deps beyond stdlib)
learning.py              (standalone -- no internal deps beyond stdlib)
signals/detector.py      (standalone -- no internal deps beyond stdlib)
adapters/base.py         (imports core.Rule only)
```

## Local State Layout

```
$DBNT_DIR/               # defaults to ~/.dbnt/
+-- rules/
|   +-- successes/       # Markdown rule files (1.5x weighted)
|   +-- failures/        # Markdown rule files (1.0x weighted)
+-- learnings.db         # SQLite: learnings table + rule_decay table
+-- score.json           # Protocol score history (JSON)
```

## Constraints

- **Performance:** Pattern detection is O(n^2) via SequenceMatcher. Capped at 200 learnings by default. `--limit` flag for manual override.
- **Security:** Zero network calls in core storage/protocol paths. Ollama extraction is opt-in and local-only. No API keys or telemetry. State is user-owned under `DBNT_DIR` (default `~/.dbnt/`).
- **Cost:** $0. No cloud services. No API keys. No subscriptions.
- **Compatibility:** Python 3.10+ (uses `X | Y` union syntax). Tested on 3.10-3.13.
