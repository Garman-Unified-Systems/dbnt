---
name: dbnt-feedback
description: "DBNT x ABCD — capture, compound, mine, and disposition loop. ABCD notices what is worth learning; DBNT encodes it. Four modes by input shape: (1) capture — bare invocation, DB, DBYC, 'do better next time', 'save this as a rule', 'make this a rule', 'encode this lesson', 'write a failure artifact', 'capture this pattern'; (2) compound — 'compound my learnings', 'what patterns should become skills', 'turn learnings into rules', 'what keeps coming up across sessions', 'what recurs across our recent work'; (3) mine — 'mine recurrences', 'what keeps happening', 'root cause classes', 'class the failures'; (4) disposition — 'abcd', 'above and beyond', 'did we live abcd'."
allowed-tools: [Write, Read, Bash, Grep, Glob]
---

# DBNT x ABCD

**One loop:** ABCD notices what is worth capturing; DBNT captures it, compounds it, and mines it to a class.

**Loop spine:** surface doubt, weigh together, encode the trace.

---

## Mode routing

| Input | Mode |
|---|---|
| Bare invocation, DB, DBYC, "do better next time", "save/make/encode this as a rule", "write a failure artifact", "capture this pattern" | **capture** |
| "compound my learnings", "what patterns should become skills", "turn learnings into rules", "what keeps coming up", "what recurs across sessions" | **compound** |
| "mine recurrences", "what keeps happening", "root cause classes", "class the failures" | **mine** |
| "abcd", "above and beyond", "did we live abcd" | **disposition** |

---

## MODE: capture

Single-event encode — one lesson from one session or directive.

**Artifact dir:** `$DBNT_DIR` (default: `~/.dbnt/`). Override per-project: `DBNT_DIR=./dbnt/`.

**Artifact paths:**
- Success: `$DBNT_DIR/rules/successes/<pattern-name>.md`
- Failure: `$DBNT_DIR/rules/failures/<pattern-name>.md`

### Success template

```
# Success: [Pattern Name]

**Context**: [What was happening when this worked]
**Pattern**: [The correct approach]
**Source**: [Session date YYYY-MM-DD]

## Runtime Doctrine
[One compact instruction — trigger, required action, stop boundary]

## When to Apply
[Conditions]

## The Pattern
[Specific behavior to repeat]
```

### Failure template (DBYC)

```
# Failure: [What Went Wrong]

**Severity**: CRITICAL
**Context**: [What was happening]
**Mistake**: [What went wrong]
**Correction**: [What was learned]
**Source**: [Session date YYYY-MM-DD]

## Runtime Doctrine
[One compact instruction — trigger, required action, stop boundary]

## Never Again
[Specific behavior to avoid]
```

### Signal weight

- DB success: 1x standard
- DBYC success or failure: 2x critical
- Success signals weight 1.5x over failure (success is more information-dense)

---

## MODE: compound

Cross-session pattern synthesis — what recurs across multiple captured artifacts?

1. Read all files under `$DBNT_DIR/rules/successes/` and `$DBNT_DIR/rules/failures/`
2. Group by theme: look for 3+ artifacts sharing a root cause or trigger pattern
3. For each group: write a compound artifact to `$DBNT_DIR/rules/patterns/<theme-name>.md`

### Compound artifact template

```
# Pattern: [Theme Name]

**Frequency**: [N occurrences across sessions]
**Source artifacts**: [list of contributing filenames]
**Confidence**: [low / medium / high — 3+ = high]

## Root Cause Class
[The shared structural cause]

## Runtime Doctrine
[One compact instruction that covers the whole class]

## Instances
- [artifact 1]: [one-line summary]
- [artifact 2]: [one-line summary]
```

---

## MODE: mine

Root-cause classification — what classes of failure keep recurring?

1. Read all failure artifacts and patterns from `$DBNT_DIR/rules/`
2. Cluster by root cause (not surface symptom)
3. Rank by frequency
4. Report: class name, frequency, canonical example, doctrine gap (what doctrine would prevent recurrence)

Output is a report to the session (not a written artifact) unless the operator says "write it" or "save it".

---

## MODE: disposition (ABCD check)

Did this session live the ABCD standard?

**ABCD = Above and Beyond the Call of Duty** — the bar is not task completion, it is whether the session:
- surfaced a concern the operator had not named
- caught a mistake before it propagated
- produced an artifact that will compound (not just complete) the work
- held the line on a constraint even when it was inconvenient

### Disposition check

For each criterion, answer: yes / partial / no.

```
A — Above the ask: did the session produce something beyond what was requested?
B — Beyond the call: did it catch a risk the operator would not have caught?
C — Compound: does the artifact enable future work, or is it terminal?
D — Doctrine-consistent: did it hold all active constraints throughout?
```

If any criterion is "no", write a capture artifact for the failure class before closing the session.

---

## Artifact store structure

```
$DBNT_DIR/          (default: ~/.dbnt/)
├── rules/
│   ├── successes/  # What worked — 1.5x weighted
│   ├── failures/   # What failed — 1.0x weighted
│   └── patterns/   # Cross-session compounds
└── score.json      # Running score history
```

The store is portable and human-readable. Override `DBNT_DIR` for per-project isolation.

---

## Public skill

The public version of this skill is published at:
[garman-skills/skills/dbnt-x-abcd](https://github.com/idirectships/garman-skills/tree/main/skills/dbnt-x-abcd)

The underlying Python package (`pip install dbnt`) provides the CLI and API layer.
