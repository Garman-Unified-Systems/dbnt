---
name: dbnt-feedback
description: "Encode what happened, surface what recurs, and check how you showed up. Invoke with any natural feedback phrase — 'do better', 'do better next time', 'that was wrong', 'that worked well', 'capture this', 'save this as a rule', 'make this a rule', 'encode this lesson', 'write a failure artifact', 'capture this pattern', 'what keeps happening', 'what keeps coming up across sessions', 'what recurs across our recent work', 'turn learnings into rules', 'compound my learnings', 'what patterns should become skills', 'mine recurrences', 'root cause classes', 'class the failures', 'abcd', 'above and beyond', 'did we live abcd'. The skill reads context and classifies the action automatically."
allowed-tools: [Write, Read, Bash, Grep, Glob]
---

# DBNT x ABCD

**Give feedback. The skill does the rest.**

ABCD notices what is worth capturing; DBNT encodes it, compounds it across sessions, and mines it to a class. The loop spine: surface doubt, weigh together, encode the trace.

---

## Auto-classification

The skill reads context and selects its own mode. You never pick a command.

**Single event** — feedback on one thing that just happened, one lesson from this session, or any phrase like "do better", "that was wrong", "that worked", "capture this":
→ **capture mode**

**Across sessions** — "what keeps coming up", "compound our learnings", "what should become a rule", patterns that span multiple past sessions:
→ **compound mode**

**Pattern classes** — "mine recurrences", "what keeps happening structurally", "root cause classes":
→ **mine mode**

**Disposition check** — "above and beyond", "abcd", "did we live it":
→ **disposition mode**

If the context is genuinely ambiguous between capture and compound, default to capture and note the compound signal for the next invocation.

---

## Capture mode

Single-event encode — one lesson from one session or directive.

**Artifact dir:** `$DBNT_DIR` (default: `~/.dbnt/`). Override per-project with `DBNT_DIR=./dbnt/`.

**Paths:**
- What worked: `$DBNT_DIR/rules/successes/<pattern-name>.md`
- What failed: `$DBNT_DIR/rules/failures/<pattern-name>.md`

**Auto-classify success vs failure from context.** The operator does not pick. Phrases like "that worked", "good pattern", "ship it" → success. Phrases like "that was wrong", "do better", "never again" → failure. Ambiguous → ask one question before writing.

**Severity is also inferred.** Incidental misses → standard. Repeated misses, high-cost errors, or explicit emphasis → critical (2x weight). A success path is weighted 1.5x over a failure path regardless of severity — a working route is rarer and more information-dense than a broken one.

### Success artifact

```markdown
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

### Failure artifact

```markdown
# Failure: [What Went Wrong]

**Severity**: [STANDARD | CRITICAL]
**Context**: [What was happening]
**Mistake**: [What went wrong]
**Correction**: [What was learned]
**Source**: [Session date YYYY-MM-DD]

## Runtime Doctrine
[One compact instruction — trigger, required action, stop boundary]

## Never Again
[Specific behavior to avoid]
```

---

## Compound mode

Cross-session synthesis — what recurring patterns should become permanent skills, rules, or hooks?

Every compound learning traces to a gap discovered in work. DBNT is the sole source of improvement.

### Process

1. **Gather** — read recent artifacts from `$DBNT_DIR/rules/`. Default window: last 7 days.
2. **Extract** — pull `## Runtime Doctrine`, `## The Pattern`, `## Never Again` from each file.
3. **Consolidate** — merge patterns expressing the same principle before counting. Three phrasings of the same lesson = one signal, not three.
4. **Threshold** — 1 occurrence: note only. 2: present. 3+: recommend creation. 4+: create.
5. **Categorize:**
   - Sequence of steps? → SKILL
   - Fires automatically on an event? → HOOK
   - "When X, do Y" heuristic? → RULE
   - Enhances existing workflow? → UPDATE
6. **Propose** — show pattern name, signal count, artifact type, draft content, target path. Get approval before writing. Summarize what was created and what was skipped.

---

## Mine mode

Cluster a window of events into root-cause classes. Classes fix the pattern; instance fixes leave the pattern intact.

Default window: last 7 days. An explicit argument overrides it; record the window in your output.

### The six canonical classes

| # | Class | Description |
|---|---|---|
| 1 | Unvalidated instrument | Checker never proven able to return the other answer on the object it judges |
| 2 | Fixed the instance, not the class | Scope from the report, not a corpus sweep; closure allowed with known-open siblings |
| 3 | Shipped is not running | merged != on-disk != registered != armed != invoked; last hop unmeasured |
| 4 | Correction lands as prose or noise | A warn rule or doc substitutes for a mechanism |
| 5 | Closure on an unprobed reference | verified-by is free text the closing author writes |
| 6 | A denial is an obstacle, not a stop | Bypass classes added instead of one stop |

Class 2 is the meta-trap: this skill exists to prevent it.

### Steps

1. Set and record the window.
2. Gather corpus — receipts, handoffs, failure artifacts, open issues, reopened items.
3. Classify each instance against the six classes in order; assign the first that fits. Hold genuinely unclassed instances (need 4+ before proposing class 7).
4. Count and rank — table by count descending with a top exemplar per class.
5. Name the encoding gap — what would close each class, and why has it not closed?
6. Report — lead with total count, classes found, largest class.

---

## Disposition mode

ABCD is an agent lifestyle trait — default character, not a checklist step invoked at session end.

**Trait:** See adjacent blockages. CAPTURE without being told. Route to the right specialist. Ask smart before silent-stuck. Bounded by Duty.

Duty bounds the trait: sealed allotments, governance hooks, custody gates.

### ABCD axes

| Axis | Behavior |
|---|---|
| **Above** | Do not stop at ticket-closed if one small step prevents rework |
| **Beyond** | Fix the leak at the joint — do not lay new pipe |
| **Call of Duty** | Stay inside the sealed allotment and stop condition |
| **Duty** | Identity, governance hooks, custody boundaries, ToS |

### Ambient check (continuous, not end-of-task ritual)

- What breaks next if I stop here?
- Can downstream consume this without another hop?
- Am I inventing or asking smart?

### Decision table

| Situation | Live ABCD? | Action |
|---|---|---|
| Work done, adjacent node blind | Yes | Mirror — do not wait to be told |
| Handoff done, not indexed | Yes | CAPTURE without prompt |
| PR open, CI green | Yes | Poll merge lane |
| Blocked on gate or taste | No | Smart ask — not parallel invent |
| New feature outside allotment | No | Smart ask or seal allotment first |

### Anti-patterns

Performative heroics, busywork, scope creep without allotment, gate bypass, invoke-only ABCD (reduces trait to checklist), unbounded polish past stop condition.

---

## The loop in full

ABCD is the front half: notice what is worth capturing, surface doubt honestly, bring the adjacent thing to the table.

DBNT is the back half: encode the talk-out trace so the same doubt never needs the same conversation twice. The artifact records the reasoning that resolved the issue — not just the mistake — so future encounters cite the resolution.

The loop closes when the artifact enters the shared guidance surface and future sessions load it at equip time.

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

The public version of this skill is also published at:
[garman-skills/skills/dbnt-x-abcd](https://github.com/idirectships/garman-skills/tree/main/skills/dbnt-x-abcd)

The underlying Python package (`pip install dbnt`) provides the CLI and API layer.
