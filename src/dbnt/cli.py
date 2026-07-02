"""DBNT CLI — Four letters to make AI better."""

from __future__ import annotations

import click

from dbnt.adapters.claude_code import ClaudeCodeAdapter
from dbnt.adapters.generic import GenericAdapter
from dbnt.core import check_dissonance, encode_failure, encode_success
from dbnt.learning import DecayEngine, LearningStore, PatternDetector
from dbnt.protocol import Protocol
from dbnt.signals import detect_signal


@click.group()
@click.version_option()
def main() -> None:
    """DBNT — Do Better Next Time

    Universal learning protocol for AI systems.
    Feedback-driven. Signal-driven. Learning-driven.
    """
    pass


# ─── Protocol Commands ─────────────────────────────────────────────────────

@main.command()
@click.argument("text")
def process(text: str) -> None:
    """Process text through the DBNT protocol.

    Detects DB/DBN/DBNM/DBYC commands and positive/negative signals.

    Example: dbnt process "dbnm"
    """
    protocol = Protocol()
    response = protocol.process(text)

    if response.command.value == "none":
        # Fall back to signal detection
        signal = detect_signal(text)
        click.echo(f"Signal: {signal.type.value} ({signal.strength.value})")
        click.echo(f"Weight: {signal.weight}")
        if signal.should_encode():
            click.echo("→ Consider encoding this as a rule")
    else:
        click.echo(f"Command: {response.command.value.upper()}")
        click.echo(f"Points: {response.points:+.1f}")
        click.echo(f"Action: {response.action.value}")
        click.echo(f"→ {response.response_text}")


@main.command()
def score() -> None:
    """Show current protocol score and history."""
    protocol = Protocol()
    state = protocol.state

    click.echo(f"Total Points: {state.total_points:+.1f}")
    click.echo(f"Success Rate: {state.success_rate:.0%}")
    click.echo(f"Events: {len(state.events)} ({state.success_count} good, {state.failure_count} bad)")

    if state.events:
        click.echo("\nRecent:")
        for event in state.events[-5:]:
            click.echo(f"  {event['command'].upper():5s} {event['points']:+.1f}  {event['timestamp'][:19]}")


# ─── Signal Detection ──────────────────────────────────────────────────────

@main.command()
@click.argument("text")
def detect(text: str) -> None:
    """Detect signal type from text.

    Example: dbnt detect "that's perfect"
    """
    signal = detect_signal(text)
    click.echo(f"Type: {signal.type.value}")
    click.echo(f"Strength: {signal.strength.value}")
    click.echo(f"Weight: {signal.weight}")
    if signal.match:
        click.echo(f"Match: {signal.match}")
    click.echo(f"Should encode: {signal.should_encode()}")


# ─── Rule Encoding ─────────────────────────────────────────────────────────

@main.command()
@click.argument("pattern")
@click.option(
    "--category", "-c",
    type=click.Choice(["format", "code", "explain", "tool", "comm"]),
    required=True,
)
@click.option("--context", "-x", default="", help="Why it worked")
def success(pattern: str, category: str, context: str) -> None:
    """Encode a success pattern.

    Example: dbnt success "Used dataclass for config" -c code -x "Clean and typed"
    """
    rule = encode_success(
        category=category,
        pattern=pattern,
        context=context or "User approved this pattern",
    )
    click.echo(f"✓ Encoded success: {rule.id}")


@main.command()
@click.argument("pattern")
@click.option(
    "--category", "-c",
    type=click.Choice(["protocol", "preference", "waste", "gap", "integration"]),
    required=True,
)
@click.option("--context", "-x", default="", help="Why it failed")
def failure(pattern: str, category: str, context: str) -> None:
    """Encode a failure pattern.

    Example: dbnt failure "Used npm instead of bun" -c protocol -x "Project requires bun"
    """
    rule = encode_failure(
        category=category,
        pattern=pattern,
        context=context or "This pattern caused issues",
    )
    click.echo(f"✗ Encoded failure: {rule.id}")


# ─── Learning System ───────────────────────────────────────────────────────

@main.command()
@click.argument("text")
@click.option("--domain", "-d", default="general", help="Learning domain")
@click.option("--importance", "-i", default=1.0, type=float, help="Importance (0-10)")
@click.option("--source", "-s", default="cli", help="Source identifier")
def learn(text: str, domain: str, importance: float, source: str) -> None:
    """Record a learning for pattern detection.

    Example: dbnt learn "Always use timezone-aware datetimes" -d code -i 3
    """
    with LearningStore() as store:
        learning_id = store.add(text=text, domain=domain, importance=importance, source=source)
    click.echo(f"Recorded learning #{learning_id} [{domain}]")


@main.command()
@click.option("--domain", "-d", default=None, help="Filter by domain")
@click.option("--threshold", "-t", default=0.7, type=float, help="Similarity threshold")
@click.option("--limit", "-l", default=200, type=int, help="Max learnings to scan (default 200)")
def patterns(domain: str | None, threshold: float, limit: int) -> None:
    """Detect recurring patterns in learnings.

    Groups similar learnings and shows which are ready for promotion to rules.
    Caps at --limit entries (default 200) to keep detection fast on large stores.
    """
    with LearningStore() as store:
        learnings = store.get_unpromoted(domain=domain)

    total = len(learnings)
    if not learnings:
        click.echo("No unpromoted learnings found.")
        return

    # Cap to avoid O(n²) timeout on large stores
    if total > limit:
        click.echo(f"Note: {total} learnings found — scanning most recent {limit} (use --limit to adjust).")
        learnings = learnings[:limit]

    detector = PatternDetector(similarity_threshold=threshold)
    groups = detector.detect(learnings)

    if not groups:
        click.echo(f"{len(learnings)} learnings, no recurring patterns yet.")
        return

    for group in groups:
        promote = "→ PROMOTE" if group.should_promote else ""
        click.echo(f"\n[{group.count}x] {group.confidence} confidence {promote}")
        click.echo(f"  \"{group.representative[:80]}\"")
        click.echo(f"  Domain: {group.domain}")


@main.command()
@click.option("--domain", "-d", default=None, help="Filter by domain")
@click.option("--limit", "-l", default=200, type=int, help="Max learnings to scan (default 200)")
def promote(domain: str | None, limit: int) -> None:
    """Auto-promote recurring patterns to rules.

    Patterns with 3+ occurrences become rules automatically.
    """
    from dbnt.signals import detect_signal

    with LearningStore() as store:
        learnings = store.get_unpromoted(domain=domain)
        if len(learnings) > limit:
            learnings = learnings[:limit]

        detector = PatternDetector()
        groups = detector.detect(learnings)

        promoted = 0
        for group in groups:
            if not group.should_promote:
                continue

            # Detect if the pattern is positive or negative
            signal = detect_signal(group.representative)
            if signal.type.value == "positive":
                rule = encode_success(
                    category="code",
                    pattern=group.representative,
                    context=f"Auto-promoted from {group.count} learnings ({group.confidence} confidence)",
                )
            else:
                rule = encode_failure(
                    category="protocol",
                    pattern=group.representative,
                    context=f"Auto-promoted from {group.count} learnings ({group.confidence} confidence)",
                )

            member_ids = [m["id"] for m in group.members if "id" in m]
            if member_ids:
                store.mark_promoted(member_ids, rule.id)

            promoted += 1
            click.echo(f"✓ Promoted: \"{group.representative[:60]}\" ({group.count}x → {rule.id})")

    store.close()

    if promoted == 0:
        click.echo("No patterns ready for promotion (need 3+ occurrences).")
    else:
        click.echo(f"\n{promoted} pattern(s) promoted to rules.")


@main.command()
def sweep() -> None:
    """Run decay sweep — check all rules for staleness.

    Shows which rules are healthy, need review, or should be archived.
    """
    from dbnt.core import get_store

    store = get_store()
    rules = store.load_all()

    if not rules:
        click.echo("No rules found.")
        return

    learning_store = LearningStore()
    engine = DecayEngine(learning_store)

    rule_ids = [r.id for r in rules]
    result = engine.sweep(rule_ids)
    learning_store.close()

    click.echo(f"Rules: {len(rules)} total")
    click.echo(f"  Healthy: {len(result['healthy'])}")
    click.echo(f"  Review:  {len(result['review'])}")
    click.echo(f"  Archive: {len(result['archive'])}")

    if result["review"]:
        click.echo("\nNeeds review:")
        for rid in result["review"]:
            click.echo(f"  ⚠ {rid}")

    if result["archive"]:
        click.echo("\nReady to archive:")
        for rid in result["archive"]:
            click.echo(f"  ✗ {rid}")


# ─── Dissonance & Status ──────────────────────────────────────────────────

@main.command()
def dissonance() -> None:
    """Check learning dissonance (success/failure balance)."""
    result = check_dissonance()

    click.echo(f"Dissonance: {result.score:.1%} ({result.status})")
    click.echo(f"Rules: {result.success_count} success, {result.failure_count} failure")

    total = result.success_count + result.failure_count
    if total > 0:
        pct = result.success_count / total
        bar_len = 30
        filled = int(pct * bar_len)
        click.echo(f"[{'█' * filled}{'░' * (bar_len - filled)}] {pct:.0%} success")

    if result.recommendation:
        click.echo(f"→ {result.recommendation}")


@main.command()
def status() -> None:
    """Show full DBNT status."""
    # Protocol score
    protocol = Protocol()
    state = protocol.state

    click.echo("DBNT Status")
    click.echo("=" * 40)
    click.echo(f"Score: {state.total_points:+.1f} ({len(state.events)} events)")
    click.echo(f"Success Rate: {state.success_rate:.0%}")

    # Dissonance
    result = check_dissonance()
    click.echo(f"Dissonance: {result.score:.1%} ({result.status})")
    click.echo(f"Rules: {result.success_count}S / {result.failure_count}F")

    # Learnings
    learning_store = LearningStore()
    counts = learning_store.count()
    total_learnings = sum(counts.values())
    learning_store.close()
    click.echo(f"Learnings: {total_learnings} total")
    if counts:
        for domain, count in sorted(counts.items()):
            click.echo(f"  {domain}: {count}")

    # Adapters
    cc = ClaudeCodeAdapter()
    click.echo(f"\nClaude Code: {'✓' if cc.is_installed() else '✗'}")


# ─── Rule Inspection ───────────────────────────────────────────────────────

@main.command("rules")
def rules_cmd() -> None:
    """List all encoded rules with decay status summary.

    Shows success and failure rules with category, preview, and health.
    """
    from dbnt.core import get_store
    from dbnt.learning import DecayEngine, LearningStore

    store = get_store()
    learning_store = LearningStore()
    engine = DecayEngine(learning_store)

    success_rules = []
    failure_rules = []
    for rule in store.load_all():
        decay = engine.check(rule.id)
        retrievability = decay["retrievability"]
        if retrievability >= 0.7:
            status = "stable"
        elif retrievability >= 0.3:
            status = "decaying"
        else:
            status = "archive"

        # Boost label for highly applied rules
        applied = decay["applied_count"]
        if applied >= 5:
            status = f"boosted {applied}x"

        entry = (rule.id, rule.category.value, rule.pattern, status)
        if rule.type.value == "success":
            success_rules.append(entry)
        else:
            failure_rules.append(entry)

    learning_store.close()

    if success_rules:
        click.echo(f"SUCCESS RULES ({len(success_rules)}):")
        for rule_id, cat, pattern, decay_status in success_rules:
            preview = (pattern[:30] + "...") if len(pattern) > 30 else pattern
            click.echo(f"  {rule_id:<30s}  [{cat:<10s}]  \"{preview:<33s}\"  ({decay_status})")
    else:
        click.echo("SUCCESS RULES (0): none encoded yet")

    click.echo("")

    if failure_rules:
        click.echo(f"FAILURE RULES ({len(failure_rules)}):")
        for rule_id, cat, pattern, decay_status in failure_rules:
            preview = (pattern[:30] + "...") if len(pattern) > 30 else pattern
            click.echo(f"  {rule_id:<30s}  [{cat:<10s}]  \"{preview:<33s}\"  ({decay_status})")
    else:
        click.echo("FAILURE RULES (0): none encoded yet")

    total = len(success_rules) + len(failure_rules)
    click.echo(f"\nTotal: {total} rules ({len(success_rules)} success, {len(failure_rules)} failure)")


@main.command("show")
@click.argument("rule_id")
def show_cmd(rule_id: str) -> None:
    """Show full content of a specific rule by ID.

    Searches both successes/ and failures/ directories.

    Example: dbnt show code_20260315_100000_a1b2
    """
    from dbnt.core import get_store

    store = get_store()

    # Search both directories for the rule file
    found_path = None
    for directory in (store.success_path, store.failure_path):
        if not directory.exists():
            continue
        for path in directory.glob("*.md"):
            # Match on stem (full filename without .md) or just the rule_id portion
            if path.stem == rule_id or path.stem.endswith(rule_id) or rule_id in path.stem:
                found_path = path
                break
        if found_path:
            break

    if not found_path:
        click.echo(f"Rule not found: {rule_id}", err=True)
        click.echo("Tip: run `dbnt rules` to see all rule IDs", err=True)
        raise SystemExit(1)

    rule_type = "success" if "success" in str(found_path).lower() else "failure"

    # Parse frontmatter from the file to show structured header
    from dbnt.storage.rules import parse_rule_file
    rule = parse_rule_file(found_path)

    click.echo("---")
    click.echo(f"id: {rule.id if rule else found_path.stem}")
    click.echo(f"type: {rule_type}")
    if rule:
        click.echo(f"category: {rule.category.value}")
        click.echo(f"created: {rule.created.isoformat()}")
    click.echo("---")
    click.echo("")
    click.echo(found_path.read_text())


# ─── Install/Uninstall ─────────────────────────────────────────────────────

@main.command()
@click.option(
    "--adapter",
    type=click.Choice(["claude-code", "generic"]),
    default="generic",
)
def install(adapter: str) -> None:
    """Install DBNT into your AI system."""
    if adapter == "claude-code":
        ClaudeCodeAdapter().install()
    else:
        GenericAdapter().install()
    click.echo("Done. Start encoding learnings!")


@main.command()
@click.option(
    "--adapter",
    type=click.Choice(["claude-code", "generic"]),
    default="generic",
)
def uninstall(adapter: str) -> None:
    """Remove DBNT from your AI system."""
    if adapter == "claude-code":
        ClaudeCodeAdapter().uninstall()
    else:
        GenericAdapter().uninstall()


if __name__ == "__main__":
    main()
