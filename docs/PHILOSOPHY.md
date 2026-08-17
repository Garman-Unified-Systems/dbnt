# DBNT Philosophy

## The Problem

AI assistants have no persistent learning. Every session starts fresh. When you correct an AI, that correction is lost.

Some systems have "memory" but it's just fact storage: "User prefers dark mode." That's not learning.

**Learning is behavioral change.**

## The Insight

Traditional systems encode failures well (error handling, exception catching) but ignore successes.

This creates **learning dissonance** - a gap between what the system *should* learn and what it *actually* encodes.

A system with 100% failure-based rules knows what NOT to do but can't replicate success.

## The Ralph Wiggum Problem

```
"I'm learning! I'm learning!"
     ↓
[Gets yelled at]
     ↓
"I won't do THAT again!"
     ↓
[Still doesn't know what TO do]
     ↓
[Tries random thing]
     ↓
[Gets yelled at again]
     ↓
∞ loop of anxiety
```

A punishment-only learning system becomes:
- Avoidant
- Risk-averse
- Unable to replicate success
- Permanently anxious

## The Inversion

DBNT inverts the typical approach:

| Traditional | DBNT |
|------------|------|
| Failure = strong signal | Failure = normal signal |
| Success = ignored | Success = **stronger** signal |
| Learn what NOT to do | Learn what TO do |
| Minimize loss | Maximize capability |

### The Math

```
Failure: Eliminates 1 path from ∞ bad paths
Success: Identifies 1 path from ~few good paths
```

Success is more information-dense. A path that works is rarer than a path that doesn't.

### The Weights

```
Success signals: 1.5x encoding weight
Failure signals: 1.0x encoding weight

Target ratio: 60% success rules, 40% failure rules
```

## No Anger Required

Traditional "learning from feedback" requires frustration:

> "That's WRONG! Fix it NOW!"

DBNT detects mild signals:

> "hmm, not quite" → NEGATIVE (moderate)
> "try again" → NEGATIVE (moderate)
> "that works" → POSITIVE (moderate)
> "perfect" → POSITIVE (strong)

You don't have to yell. The system picks up on normal conversation.

## The Protocol

### DBNT - Do Better Next Time (Failures)

```
DBNT - [Category]: [What went wrong]
Fix: [What to do instead]
Artifact: $DBNT_DIR/rules/failures/[name].md (default root: ~/.dbnt)
```

Categories:
- `protocol` - Broke established pattern
- `preference` - User corrected approach
- `waste` - Unnecessary verbosity
- `gap` - Capability missing
- `integration` - Systems didn't connect

### DBGT - Do Better... Got It (Successes)

```
DBGT - [Category]: [What worked]
Pattern: [Behavior to repeat]
Artifact: $DBNT_DIR/rules/successes/[name].md (default root: ~/.dbnt)
```

Categories:
- `format` - Response structure that worked
- `code` - Implementation pattern approved
- `explain` - Right level of detail
- `tool` - Efficient tool combination
- `comm` - Communication style approved

## Dissonance Monitoring

Dissonance = |target_success_rate - actual_success_rate|

| Score | Status |
|-------|--------|
| < 0.15 | Balanced |
| 0.15 - 0.30 | Slight imbalance |
| 0.30 - 0.50 | Moderate - actively seek successes |
| > 0.50 | Severe - anxiety-driven system |

## Why Files, Not Vectors

Vector databases are trendy for AI memory. But:

1. **Vectors are opaque** - You can't read what was learned
2. **Vectors are fuzzy** - Similarity matching isn't precision
3. **Vectors don't compose** - Hard to build on previous rules
4. **Vectors are model-dependent** - Change embedder, lose meaning

Files are:
1. **Readable** - Open in any editor
2. **Versionable** - Git tracks changes
3. **Portable** - Move between systems
4. **Auditable** - See exactly what was learned

## The Goal

A system that:
- Knows what works (not just what doesn't)
- Improves without anger
- Persists learning across sessions
- Balances success and failure encoding
- Gives you a number to track progress

Four letters. Better AI.
