---
trigger: always_on
---

# DBNT Devin Rules

This repository is public. Work only within this repository and only on the
files named by the task. Do not search the host, inspect user data, or infer
access beyond the checked-out public source.

Use a feature branch. Never merge, deploy, restart services, change credentials,
or mutate task queues. Stop on scope drift, unclear requirements, protected data,
or repeated failure.

For the first pilot, production code is read-only. The only writable task file
is `tests/test_cli.py`, and the worker has no shell-execution tool. Stop after
preparing that file. An independent verifier runs the focused test, repository
gate, and diff checks. Report the current commit, exact diff, limitations, and
model usage when available. Unknown usage is not zero.

Devin Knowledge is derived guidance, not a source of truth. Repository source,
tests, and the reviewed pull request are authoritative for this task.
