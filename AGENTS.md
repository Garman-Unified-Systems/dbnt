# AGENTS.md -- AI Developer Guide for DBNT

<!-- LIFECYCLE -->
- **Phase:** PRODUCTION
- **Owner:** dru
- **Deploy:** PyPI (v0.5.2)
- **Sensitivity:** PUBLIC
- **Last Session:** 2026-03-28
- **Status:** Universal feedback protocol for AI agents
<!-- /LIFECYCLE -->

## Project Overview
DBNT (Do Better Next Time) is a feedback protocol and learning system for AI agents. It encodes human corrections as persistent, weighted rules using local storage (markdown files + SQLite). Published on PyPI as `dbnt`. MIT licensed.

## Standard Docs
- [architecture.md](architecture.md) -- Package structure, dependencies, build/publish pipeline
- [prd.md](prd.md) -- Vision, users, features, success criteria
- [white.md](white.md) -- Problem statement, solution, market positioning
- [yellow.md](yellow.md) -- Protocol spec, signal types, scoring rules, data structures

## Development Setup
```bash
git clone https://github.com/idirectships/dbnt.git
cd dbnt
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest  # verify setup
```

## Project Structure
```
src/dbnt/
├── __init__.py          # Public API exports (27 symbols)
├── __main__.py          # Entry point for `python -m dbnt`
├── cli.py               # Click CLI (all user-facing commands)
├── core.py              # Rule encoding, storage, retrieval, dissonance
├── protocol.py          # DB/DBN/DBNM/DBYC command processing + scoring
├── extract.py           # Transcript parsing (regex + optional Ollama)
├── learning.py          # Pattern detection, FSRS decay, auto-promotion
├── adapters/
│   ├── base.py          # BaseAdapter interface (5 abstract methods)
│   ├── claude_code.py   # Claude Code hooks adapter
│   └── generic.py       # File-based generic adapter
├── signals/
│   └── detector.py      # Natural language signal classification
└── storage/
    └── rules.py         # Markdown rule file I/O + parsing
```

## Architecture Decisions
- **Markdown rules, not vectors** -- human-readable, git-trackable, auditable
- **FSRS-6 for decay** -- proven spaced-repetition algorithm, not custom
- **click for CLI** -- only runtime dependency; everything else is stdlib
- **Adapter pattern** -- new integrations don't touch core logic
- **Local-first** -- no cloud, no API keys, no external services required
- **Success 1.5x weighting** -- information-theoretic: working paths are rarer than broken ones

## Code Conventions
- Type hints on all public functions
- Dataclasses for structured data (Signal, Rule, ExtractedLearning, DecayState)
- `pathlib.Path` throughout (no os.path)
- Tests mirror source structure: `test_protocol.py` tests `protocol.py`
- `ruff` for linting, `mypy` for type checking (strict mode)

## Common Tasks

### Run tests
```bash
pytest tests/ -v
```

### Type check
```bash
mypy src/
```

### Lint
```bash
ruff check src/ tests/
```

### Build + Publish
```bash
python -m build
twine upload dist/*
```

## Adding a New Adapter

1. Create `src/dbnt/adapters/my_adapter.py`
2. Inherit from `BaseAdapter` in `adapters/base.py`
3. Implement required methods: `install()`, `uninstall()`, `sync_rule()`, `get_rules_path()`, `is_installed()`
4. Register entry point in `pyproject.toml`:
   ```toml
   [project.entry-points."dbnt.adapters"]
   my_adapter = "dbnt.adapters.my_adapter:MyAdapter"
   ```
5. Add tests in `tests/test_adapters/test_my_adapter.py`
6. Document in `docs/ADAPTERS.md`

## Adding a New Signal Pattern

1. Edit `src/dbnt/signals/detector.py`
2. Add pattern to appropriate list: `POSITIVE_STRONG`, `POSITIVE_MODERATE`, `NEGATIVE_STRONG`, `NEGATIVE_MODERATE`
3. Patterns are regex-based, case-insensitive
4. Add test case in `tests/test_signals.py`

## Debugging

```bash
# View encoded rules
ls ~/.dbnt/rules/successes/
ls ~/.dbnt/rules/failures/
cat ~/.dbnt/rules/successes/<rule-id>.md

# Query learning database
sqlite3 ~/.dbnt/learnings.db "SELECT * FROM learnings ORDER BY created DESC LIMIT 10;"

# Check decay status
dbnt sweep --dry-run

# View current score
dbnt score
```

## PR Guidelines
- All PRs need passing tests (`pytest`)
- Type-check clean (`mypy src/`)
- Lint clean (`ruff check`)
- New features need tests
- Core protocol changes require discussion in an issue first
- Adapter PRs are welcome without prior discussion
