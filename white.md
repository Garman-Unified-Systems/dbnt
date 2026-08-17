# White Paper -- DBNT

> Notion: https://www.notion.so/331b18c770b281cea49ffb5b2661eed9

## Problem

AI agents make the same mistakes every session. You correct them, they improve within the conversation, and then the context window resets. Next session, same mistakes.

This is the structured feedback gap. Unstructured corrections ("that's wrong, try again") don't transfer across sessions, don't distinguish severity, and don't accumulate into durable knowledge. The agent improves in the moment, then forgets. You correct the same thing next week.

The failure mode compounds. AI agents generating plausible but unsupported output -- hallucination -- is documented across every major provider. When the correction loop is ad-hoc, these errors recur without accumulating toward resolution.

Traditional memory systems record what went wrong, creating agents that know a hundred ways to fail but can't reliably replicate success. This is the Ralph Wiggum Problem: knowing 100 things not to do doesn't tell you what to do.

## Solution

DBNT (Do Better Next Time) is a local feedback protocol and rule-lifecycle toolkit. It classifies feedback and gives callers explicit operations for persisting weighted learning rules.

Four explicit commands (DB, DBN, DBNM, DBYC) return correction actions. A separate signal detector classifies common natural-language phrases such as "not quite" and "perfect." Encoding is explicit: the caller invokes the success or failure API/CLI to create a human-readable markdown file. Success rules default to 1.5x weight.

Rules persist across sessions. Explicit reviews and boosts change FSRS-inspired decay state. `dbnt sweep` reports healthy, review, and archive candidates but does not move files. `dbnt promote` can promote groups of three or more similar learning rows when an operator runs it. Archival remains an operator or host action.

No cloud. No API keys. No external services. Everything runs locally. The rule store is a directory of markdown files and a SQLite database. You own all of it.

## How It Works

1. **You provide feedback.** Pass a protocol command to `dbnt process` or text to `dbnt detect`.
2. **DBNT returns structured information.** The caller receives an action or signal classification.
3. **The caller encodes deliberately.** `dbnt success` or `dbnt failure` writes under `$DBNT_DIR/rules/` (default `~/.dbnt`).
4. **The host consumes rules.** DBNT 0.6.0 does not inject them into prompts automatically.
5. **Operators manage lifecycle.** Learnings can be grouped/promoted; decay state can be reviewed/boosted; sweep reports candidates.

The local store requires no server. Host-side rule loading, archival, distributed synchronization, and concurrency controls are separate integration work.

## Market

- **Size:** The AI agent ecosystem is early and expanding. Every developer using Claude Code, Cursor, LangChain, CrewAI, AutoGen, or custom agent frameworks is a potential user. The "AI memory" category is nascent -- most solutions are cloud-hosted vector databases that solve a different problem (retrieval, not learning).

- **Competitors:**
  - **mem0** -- Cloud-hosted memory layer. Requires API keys, external storage. Optimized for retrieval, not structured feedback.
  - **Letta (MemGPT)** -- Agent-managed memory with self-editing. Complex, tied to specific architectures.
  - **Zep** -- Session memory + knowledge graphs. Cloud-first, enterprise-focused.
  - **Custom .cursorrules / CLAUDE.md** -- Manual rule files. No lifecycle, no weighting, no automation.

- **Our edge:**
  - Local-first (zero cloud, zero API keys)
  - Structured feedback protocol (severity-graded, not thumbs-up/down)
  - Success-weighted encoding (information-theoretic basis)
  - FSRS-6 decay (proven algorithm, not custom)
  - LLM-agnostic (works with any model, any tool)
  - One dependency (click)

## Business Model

DBNT is open source (MIT). The protocol and library are free.

The package is intentionally local and composable. A distributed coordination product could build on its rule format, but transport, cross-agent propagation, concurrency control, and peer review are not capabilities of DBNT 0.6.0.

Value flows from adoption: more users -> more adapters -> more integrations -> more demand for the production coordination layer that sits above it.

## Roadmap

| Phase | What | When |
|-------|------|------|
| 1 | Core protocol, signal detection, CLI, Claude Code adapter | Done (v0.2.0) |
| 2 | FSRS decay, pattern promotion, transcript extraction, CI | Done (v0.5.0) |
| 3 | Performance hardening, dedup, contamination filter | Done (v0.5.2) |
| 4 | One `DBNT_DIR` state-root contract, hook/release robustness | 0.6.0 release candidate |
| 5 | Adapter expansion after compatibility review | Planned |
| 6 | Stable v1.0 API; distributed coordination separately scoped | Planned |
