"""DBNT CLI — Four letters to make AI better."""

from __future__ import annotations

import json
from itertools import chain
from typing import TYPE_CHECKING

import click

from dbnt.adapters.claude_code import ClaudeCodeAdapter
from dbnt.adapters.generic import GenericAdapter
from dbnt.agency import (
    ActionProposal,
    Boundary,
    Disposition,
    Effect,
    classify_action,
    default_regression_cases,
    evaluate_cases,
)
from dbnt.core import RuleType, check_dissonance, encode_failure, encode_success
from dbnt.learning import DecayEngine, LearningStore, PatternDetector
from dbnt.protocol import Protocol
from dbnt.seats import (
    SEAT_CATEGORIES,
    SeatError,
    capture_seat_rule,
    decay_key,
    list_seat_names,
    load_seat_rules,
    render_prompt_block,
    validate_seat,
)
from dbnt.signals import detect_signal

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from dbnt.core import RuleStore
    from dbnt.learning import PatternGroup


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


@main.command("agency-check")
def agency_check() -> None:
    """Run the deterministic MOVE/GATE/DROP regression suite."""
    result = evaluate_cases(default_regression_cases())
    if result.passed:
        click.echo("Bounded agency: PASS")
        click.echo(f"{result.passing}/{result.total} regression cases")
        return

    click.echo("Bounded agency: FAIL", err=True)
    for failure in result.failures:
        click.echo(
            f"  {failure.case_name}: expected {failure.expected.value}, "
            f"got {failure.actual.value}",
            err=True,
        )
    raise click.exceptions.Exit(1)


@main.command("agency-decide")
@click.option("--name", required=True, help="Human-readable action name")
@click.option(
    "--effect",
    type=click.Choice([effect.value for effect in Effect]),
    required=True,
    help="Observable action effect; required to prevent permissive omission",
)
@click.option("--advances-outcome/--does-not-advance", default=True)
@click.option("--evidence/--no-evidence", default=False)
@click.option("--in-scope/--out-of-scope", default=True)
@click.option("--reversible/--irreversible", default=True)
@click.option(
    "--boundary",
    type=click.Choice([boundary.value for boundary in Boundary]),
    multiple=True,
)
@click.option(
    "--authorized-boundary",
    type=click.Choice([boundary.value for boundary in Boundary]),
    multiple=True,
)
@click.option("--authority-verified", is_flag=True)
@click.option("--requires-current-state", is_flag=True)
@click.option("--current-state-verified", is_flag=True)
def agency_decide(
    name: str,
    effect: str,
    advances_outcome: bool,
    evidence: bool,
    in_scope: bool,
    reversible: bool,
    boundary: tuple[str, ...],
    authorized_boundary: tuple[str, ...],
    authority_verified: bool,
    requires_current_state: bool,
    current_state_verified: bool,
) -> None:
    """Classify one runtime action; only MOVE exits successfully."""

    proposal = ActionProposal(
        name=name,
        advances_outcome=advances_outcome,
        effect=Effect(effect),
        produces_evidence=evidence,
        in_scope=in_scope,
        reversible=reversible,
        boundaries=frozenset(Boundary(value) for value in boundary),
        authorized_boundaries=frozenset(Boundary(value) for value in authorized_boundary),
        authority_verified=authority_verified,
        requires_current_state=requires_current_state,
        current_state_verified=current_state_verified,
    )
    decision = classify_action(proposal)
    click.echo(
        json.dumps(
            {
                "disposition": decision.disposition.value,
                "reasons": list(decision.reasons),
                "unmet_boundaries": [item.value for item in decision.unmet_boundaries],
            },
            sort_keys=True,
        )
    )
    if decision.disposition is Disposition.GATE:
        raise click.exceptions.Exit(2)
    if decision.disposition is Disposition.DROP:
        raise click.exceptions.Exit(3)


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


# ─── Seat Slices ───────────────────────────────────────────────────────────

def decay_label(retrievability: float, applied_count: int) -> str:
    """Return the decay status label shared by rule listings."""
    if applied_count >= 5:
        return f"boosted {applied_count}x"
    if retrievability >= 0.7:
        return "stable"
    if retrievability >= 0.3:
        return "decaying"
    return "archive"


def rule_row(rule_id: str, category: str, pattern: str, status: str) -> str:
    """Render one rule line in the `dbnt rules` format."""
    preview = (pattern[:30] + "...") if len(pattern) > 30 else pattern
    return f"  {rule_id:<30s}  [{category:<10s}]  \"{preview:<33s}\"  ({status})"


def seat_targets(seat: str | None, list_all: bool) -> list[str]:
    """Resolve which seats a listing request names."""
    if seat and list_all:
        raise click.ClickException("--all takes no seat argument")
    if list_all:
        return list_seat_names()
    if not seat:
        raise click.ClickException("Missing argument 'SEAT'.")
    return [validate_seat(seat)]


def echo_seat_listing(seat: str, prompt: bool, engine: DecayEngine) -> None:
    """Print one seat slice, either as a prompt block or as a decay listing."""
    rules = load_seat_rules(seat)
    if prompt:
        click.echo(render_prompt_block(seat, rules))
        return

    click.echo(f"SEAT {seat} ({len(rules)}):")
    if not rules:
        click.echo("  none captured yet")
        return
    for rule in rules:
        decay = engine.check(decay_key(seat, rule.id))
        status = decay_label(decay["retrievability"], decay["applied_count"])
        click.echo(rule_row(rule.id, rule.category.value, rule.pattern, status))


def seat_decay_lines(engine: DecayEngine) -> list[str]:
    """Build the report-only seat section used by `dbnt sweep`."""
    lines = []
    for seat in list_seat_names():
        for rule in load_seat_rules(seat):
            decay = engine.check(decay_key(seat, rule.id))
            status = decay_label(decay["retrievability"], decay["applied_count"])
            lines.append(f"  {seat}  {rule.id}  ({status})")
    return lines


@main.command("seat-capture")
@click.argument("seat")
@click.argument("pattern")
@click.option(
    "--kind", "-k",
    type=click.Choice(["success", "failure"]),
    default="failure",
    show_default=True,
    help="Seat rule direction",
)
@click.option(
    "--category", "-c",
    type=click.Choice([*SEAT_CATEGORIES[RuleType.SUCCESS], *SEAT_CATEGORIES[RuleType.FAILURE]]),
    required=True,
)
@click.option("--context", "-x", default="", help="Why it failed")
@click.option("--replace", is_flag=True, help="Update an existing seat rule for the same pattern")
def seat_capture(
    seat: str, pattern: str, kind: str, category: str, context: str, replace: bool
) -> None:
    """Encode a rule into a runner seat slice.

    Example: dbnt seat-capture codex@dru "Guessed a hash" -c protocol -x "Read the file first"
    """
    try:
        capture = capture_seat_rule(
            seat=seat,
            pattern=pattern,
            kind=RuleType(kind),
            category=category,
            context=context,
            replace_existing=replace,
        )
    except SeatError as error:
        raise click.ClickException(str(error)) from error

    if capture.replaced:
        marker = "~"
    elif capture.rule.type is RuleType.SUCCESS:
        marker = "✓"
    else:
        marker = "✗"
    click.echo(f"{marker} Seat rule {capture.rule.id} ({seat})")
    click.echo(f"  {capture.path}")


@main.command("seat-rules")
@click.argument("seat", required=False)
@click.option("--prompt", is_flag=True, help="Print only a pasteable markdown block")
@click.option("--all", "list_all", is_flag=True, help="List every seat that has rules")
def seat_rules(seat: str | None, prompt: bool, list_all: bool) -> None:
    """List one seat's rules with category and decay status.

    Example: dbnt seat-rules codex@dru --prompt
    """
    try:
        names = seat_targets(seat, list_all)
    except SeatError as error:
        raise click.ClickException(str(error)) from error

    learning_store = LearningStore()
    engine = DecayEngine(learning_store)
    try:
        for name in names:
            echo_seat_listing(name, prompt, engine)
    finally:
        learning_store.close()

    if list_all and not names:
        click.echo("No seat slices found.")


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


def promote_rule(seat: str | None, pattern: str, context: str, rule_type: RuleType) -> str:
    """Promote one detected pattern into the global store or a seat slice."""
    if seat is None:
        if rule_type is RuleType.SUCCESS:
            return encode_success(category="code", pattern=pattern, context=context).id
        return encode_failure(category="protocol", pattern=pattern, context=context).id

    capture = capture_seat_rule(
        seat=seat,
        pattern=pattern,
        kind=rule_type,
        category="code" if rule_type is RuleType.SUCCESS else "protocol",
        context=context,
        replace_existing=True,
    )
    return capture.rule.id


def promote_group(store: LearningStore, group: PatternGroup, seat: str | None) -> str:
    """Promote one qualifying pattern group and report the new rule ID."""
    signal = detect_signal(group.representative)
    rule_type = RuleType.SUCCESS if signal.type.value == "positive" else RuleType.FAILURE
    rule_id = promote_rule(
        seat,
        group.representative,
        f"Auto-promoted from {group.count} learnings ({group.confidence} confidence)",
        rule_type,
    )

    member_ids = [m["id"] for m in group.members if "id" in m]
    if member_ids:
        store.mark_promoted(member_ids, rule_id)

    click.echo(f"✓ Promoted: \"{group.representative[:60]}\" ({group.count}x → {rule_id})")
    return rule_id


@main.command()
@click.option("--domain", "-d", default=None, help="Filter by domain")
@click.option("--limit", "-l", default=200, type=int, help="Max learnings to scan (default 200)")
@click.option("--seat", default=None, help="Write promoted rules into this seat slice")
def promote(domain: str | None, limit: int, seat: str | None) -> None:
    """Auto-promote recurring patterns to rules.

    Patterns with 3+ occurrences become rules automatically.
    """
    if seat is not None:
        try:
            validate_seat(seat)
        except SeatError as error:
            raise click.ClickException(str(error)) from error

    with LearningStore() as store:
        learnings = store.get_unpromoted(domain=domain)
        if len(learnings) > limit:
            learnings = learnings[:limit]

        detector = PatternDetector()
        groups = detector.detect(learnings)

        promoted = 0
        for group in groups:
            if group.should_promote:
                promote_group(store, group, seat)
                promoted += 1

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
    seats = list_seat_names()

    if not rules and not seats:
        click.echo("No rules found.")
        return

    learning_store = LearningStore()
    engine = DecayEngine(learning_store)

    rule_ids = [r.id for r in rules]
    result = engine.sweep(rule_ids)
    seat_lines = seat_decay_lines(engine)
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

    if seat_lines:
        click.echo("\nSeat rules:")
        for line in seat_lines:
            click.echo(line)


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
        status = decay_label(decay["retrievability"], decay["applied_count"])

        entry = (rule.id, rule.category.value, rule.pattern, status)
        if rule.type.value == "success":
            success_rules.append(entry)
        else:
            failure_rules.append(entry)

    learning_store.close()

    if success_rules:
        click.echo(f"SUCCESS RULES ({len(success_rules)}):")
        for entry in success_rules:
            click.echo(rule_row(*entry))
    else:
        click.echo("SUCCESS RULES (0): none encoded yet")

    click.echo("")

    if failure_rules:
        click.echo(f"FAILURE RULES ({len(failure_rules)}):")
        for entry in failure_rules:
            click.echo(rule_row(*entry))
    else:
        click.echo("FAILURE RULES (0): none encoded yet")

    total = len(success_rules) + len(failure_rules)
    click.echo(f"\nTotal: {total} rules ({len(success_rules)} success, {len(failure_rules)} failure)")


def rule_candidates(directory: Path) -> Iterator[Path]:
    """Yield rule files from a directory that may not exist."""
    if directory.exists():
        yield from directory.glob("*.md")


def matches_rule_id(path: Path, rule_id: str) -> bool:
    """Match a rule file on its full stem or on the rule ID portion."""
    return path.stem == rule_id or path.stem.endswith(rule_id) or rule_id in path.stem


def find_rule_path(store: RuleStore, rule_id: str) -> Path | None:
    """Find the first rule file matching a rule ID across both stores."""
    paths = chain(rule_candidates(store.success_path), rule_candidates(store.failure_path))
    return next((path for path in paths if matches_rule_id(path, rule_id)), None)


@main.command("show")
@click.argument("rule_id")
def show_cmd(rule_id: str) -> None:
    """Show full content of a specific rule by ID.

    Searches both successes/ and failures/ directories.

    Example: dbnt show code_20260315_100000_a1b2
    """
    from dbnt.core import get_store

    store = get_store()
    found_path = find_rule_path(store, rule_id)

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
