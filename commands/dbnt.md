---
name: dbnt
description: "DBNT protocol status and management"
argument-hint: "[status|rules|sweep|detect \"text\"]"
allowed-tools: [Bash, Read]
---

# /dbnt — Protocol Status & Management

Run DBNT CLI commands for protocol status, rule management, and signal detection.

## Dispatch

If no argument is given, run `dbnt status`.

Otherwise, pass the argument directly to the `dbnt` CLI:

```bash
dbnt $ARGUMENTS
```

## Available Commands

- `status` — Full system overview (score, rules, learnings)
- `rules` — List all active rules with decay status
- `sweep` — Report FSRS-inspired healthy/review/archive categories; does not move files
- `detect "text"` — Classify a natural language signal
- `score` — View scoring history
- `patterns` — Show recurring learning patterns
- `promote` — Auto-promote qualifying patterns to rules
- `dissonance` — Surface conflicting success/failure signals

## If dbnt is not installed

Tell the user:

```
DBNT CLI not found. Install with: pip install dbnt
```
