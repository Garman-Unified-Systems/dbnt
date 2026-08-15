# Devin Onboarding for DBNT

Devin is admitted to this public repository through bounded, independently
verifiable tasks. It is an execution worker, not a source of truth or a release
authority.

## Environment

- Python: 3.12
- Install: `python -m pip install -e '.[dev]'`
- Focused tests: `python -m pytest -q <test-path>`
- Full tests: `python -m pytest -q`
- Lint: `python -m ruff check src tests`
- Types: `python -m mypy src`

The default Devin pilot model is `swe-1-7-medium`, which the Devin model catalog
labels free. Model availability and pricing must be checked at task admission;
they are not assumed permanent.

## Operating boundary

Only public repository content is in scope. Secrets, credentials, personal data,
private repositories, local session records, and external knowledge stores are
out of scope. MCP and subagents remain disabled until separate canaries prove
their controls. The first pilot also removes shell execution from the worker;
all checks are run by an independent verifier after the edit is returned.

Every assignment names its owned files, acceptance criteria, time cap, stop
conditions, and proof commands. Devin may prepare a reviewable change on a
feature branch, but it may not merge, deploy, restart services, or alter task
queues.

## First pilot

Invoke `/dbnt-cli-tests`. The skill may create only `tests/test_cli.py`, has no
shell-execution tool, and must stop before commit or push. A separate reviewer
verifies the diff and reruns all checks against the current branch head.

## Definition of done

A task is complete only when the requested outcome and acceptance criteria are
met, focused and broader checks pass, documentation matches behavior, and the
handoff records the immutable revision, changed artifacts, exact commands and
observed output, elapsed time, model, provider usage or an unavailable-usage
blocker, and remaining risks.
