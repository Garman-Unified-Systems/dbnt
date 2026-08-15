---
name: dbnt-cli-tests
description: Add bounded Click CliRunner regression tests for the public DBNT CLI without changing production code.
model: swe-1-7-medium
subagent: false
allowed-tools:
  - read
  - edit
  - grep
  - glob
permissions:
  allow:
    - Read(src/**)
    - Read(tests/**)
    - Read(pyproject.toml)
    - Write(tests/test_cli.py)
  deny:
    - Write(src/**)
    - Write(pyproject.toml)
    - Write(.github/**)
    - Write(.devin/**)
    - mcp__*
triggers:
  - user
---

Add `tests/test_cli.py` using Click's `CliRunner` to cover only these behaviors:

1. `detect "perfect"` reports a positive, strong signal.
2. `detect "ok"` reports a neutral signal.
3. `process "dbn"` reports the DBN command path.
4. `process` with ordinary text falls back to signal detection.
5. Invalid `success --category` and `failure --category` values exit nonzero.

Read the current CLI and existing test conventions before editing. Do not change
production code or any existing test file. You do not have a shell-execution
tool in this pilot. Stop after preparing `tests/test_cli.py`; an independent
verifier will run, in order:

```text
python -m pytest -q tests/test_cli.py
python -m pytest -q
python -m ruff check tests/test_cli.py
git diff --check
git status --short
git diff -- tests/test_cli.py
```

Stop if production behavior must change, another file is required, or the task
exceeds 45 minutes. Do not attempt to execute commands, commit, push, open a
pull request, merge, or deploy.

Return a receipt with the starting commit if visible, changed file, requested
external verification commands, unresolved risks, elapsed time, model name,
and provider usage if the client exposes it. Mark unavailable usage as
unavailable. Never claim that a command passed unless the independent verifier
returns its observed output.
