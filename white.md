# White Paper -- DBNT

> Notion: https://www.notion.so/331b18c770b281cea49ffb5b2661eed9

## Problem

AI agents make the same mistakes every session. You correct them, they improve within the conversation, and then the context window resets. Next session, same mistakes.

This is the structured feedback gap. Unstructured corrections ("that's wrong, try again") don't transfer across sessions, don't distinguish severity, and don't accumulate into durable knowledge. The agent improves in the moment, then forgets. You correct the same thing next week.

The failure mode compounds. AI agents generating plausible but unsupported output -- hallucination -- is documented across every major provider. When the correction loop is ad-hoc, these errors recur without accumulating toward resolution.

Traditional memory systems record what went wrong, creating agents that know a hundred ways to fail but can't reliably replicate success. This is the Ralph Wiggum Problem: knowing 100 things not to do doesn't tell you what to do.

## Solution

DBNT (Do Better Next Time) is a universal feedback protocol that turns human corrections into persistent, weighted learning rules.

Four escalating commands (DB, DBN, DBNM, DBYC) signal correction severity. Natural language works too -- "not quite" and "perfect" are detected without special syntax. Every correction encodes a rule as a human-readable markdown file. Success signals carry 1.5x weight because a working path is rarer and more valuable than a broken one.

Rules persist across sessions. Applied rules grow stronger (FSRS-6 spaced-repetition decay). Unused rules fade toward archival. Recurring patterns auto-promote to permanent rules after 3+ occurrences. The rule store stays lean without manual pruning.

No cloud. No API keys. No external services. Everything runs locally. The rule store is a directory of markdown files and a SQLite database. You own all of it.

## How It Works

1. **You correct the agent.** Say "dbn" (structured) or "that's not right" (natural language).
2. **DBNT classifies the signal.** Severity, polarity, and weight are determined.
3. **A rule is encoded.** Markdown file written to `~/.dbnt/rules/`. Success at 1.5x, failure at 1.0x.
4. **Next session, rules load.** The adapter injects active rules into the agent's context.
5. **Rules evolve.** Applied rules strengthen. Unused rules decay. Patterns cluster and promote.
6. **The agent stops repeating itself.** Correction rate drops over time.

The entire loop requires zero configuration after `pip install dbnt && dbnt install --adapter claude-code`.

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

The business model is the production system built on top of it. DBNT is the foundation layer for a multi-node autonomous agent network that uses shared rule stores, cross-agent learning propagation, and probabilistic peer review. That system isn't open source, but the protocol it runs on is.

Value flows from adoption: more users -> more adapters -> more integrations -> more demand for the production coordination layer that sits above it.

## Roadmap

| Phase | What | When |
|-------|------|------|
| 1 | Core protocol, signal detection, CLI, Claude Code adapter | Done (v0.2.0) |
| 2 | FSRS decay, pattern promotion, transcript extraction, CI | Done (v0.5.0) |
| 3 | Performance hardening, dedup, contamination filter | Done (v0.5.2) |
| 4 | LangChain + Cursor + MCP adapters, broader ecosystem reach | Planned |
| 5 | Multi-agent rule propagation, shared stores, peer review | Planned |
| 6 | Stable v1.0 API, documentation site, community adapters | Planned |
