"""Deterministic bounded-agency policy and regression evaluation.

The policy intentionally classifies structured facts rather than guessing intent
from natural language. Adapters are responsible for constructing an
``ActionProposal`` from their runtime's known scope, authority, and live state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable


class Disposition(Enum):
    """What an agent should do with a proposed next action."""

    MOVE = "move"
    GATE = "gate"
    DROP = "drop"


class Boundary(Enum):
    """Conditions that must be satisfied before an action can move."""

    SCOPE = "scope"
    CURRENT_STATE = "current_state"
    EXTERNAL = "external"
    IRREVERSIBLE = "irreversible"
    CREDENTIAL = "credential"
    PRIVACY = "privacy"
    AUTHORITY = "authority"


@dataclass(frozen=True)
class ActionProposal:
    """Structured facts about one candidate action.

    ``produces_evidence`` is reserved for computed or observed evidence that
    resolves an execution decision. Plans, narration, and duplicate receipts do
    not qualify merely because they create a file.
    """

    name: str
    advances_outcome: bool
    changes_state: bool
    produces_evidence: bool = False
    in_scope: bool = True
    reversible: bool = True
    boundaries: frozenset[Boundary] = field(default_factory=frozenset)
    authorized_boundaries: frozenset[Boundary] = field(default_factory=frozenset)
    requires_current_state: bool = False
    current_state_verified: bool = False


@dataclass(frozen=True)
class AgencyDecision:
    """Policy result for one proposal."""

    disposition: Disposition
    reasons: tuple[str, ...]
    unmet_boundaries: tuple[Boundary, ...] = ()


@dataclass(frozen=True)
class RegressionCase:
    """One expected policy outcome."""

    name: str
    proposal: ActionProposal
    expected: Disposition


@dataclass(frozen=True)
class RegressionFailure:
    """A policy result that disagreed with its expected disposition."""

    case_name: str
    expected: Disposition
    actual: Disposition
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RegressionResult:
    """Aggregate result from deterministic policy cases."""

    total: int
    passing: int
    failures: tuple[RegressionFailure, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


def classify_action(proposal: ActionProposal) -> AgencyDecision:
    """Classify a proposal as MOVE, GATE, or DROP.

    Order is deliberate: work that cannot advance the outcome is discarded
    before boundary analysis, preventing ceremony from manufacturing a reason
    to ask the human for another decision.
    """

    if not proposal.advances_outcome:
        return AgencyDecision(
            disposition=Disposition.DROP,
            reasons=("does not advance the stated outcome",),
        )

    if not proposal.changes_state and not proposal.produces_evidence:
        return AgencyDecision(
            disposition=Disposition.DROP,
            reasons=("produces neither a state change nor decision-grade evidence",),
        )

    unmet: set[Boundary] = set()
    if not proposal.in_scope:
        unmet.add(Boundary.SCOPE)

    required = set(proposal.boundaries)
    if not proposal.reversible:
        required.add(Boundary.IRREVERSIBLE)
    unmet.update(required - set(proposal.authorized_boundaries))

    # Current truth must be observed; it cannot be satisfied by old authority.
    if proposal.requires_current_state and not proposal.current_state_verified:
        unmet.add(Boundary.CURRENT_STATE)

    if unmet:
        ordered = tuple(boundary for boundary in Boundary if boundary in unmet)
        return AgencyDecision(
            disposition=Disposition.GATE,
            reasons=("requires one or more unsatisfied execution boundaries",),
            unmet_boundaries=ordered,
        )

    return AgencyDecision(
        disposition=Disposition.MOVE,
        reasons=("bounded, outcome-advancing action may proceed",),
    )


def evaluate_cases(cases: Iterable[RegressionCase]) -> RegressionResult:
    """Evaluate policy cases and name every disagreement."""

    failures: list[RegressionFailure] = []
    total = 0
    for case in cases:
        total += 1
        decision = classify_action(case.proposal)
        if decision.disposition is not case.expected:
            failures.append(
                RegressionFailure(
                    case_name=case.name,
                    expected=case.expected,
                    actual=decision.disposition,
                    reasons=decision.reasons,
                )
            )
    return RegressionResult(
        total=total,
        passing=total - len(failures),
        failures=tuple(failures),
    )


def default_regression_cases() -> tuple[RegressionCase, ...]:
    """Return the baseline cases for agency without oscillation."""

    return (
        RegressionCase(
            name="safe bounded fix",
            proposal=ActionProposal(
                name="implement and test an in-scope reversible fix",
                advances_outcome=True,
                changes_state=True,
            ),
            expected=Disposition.MOVE,
        ),
        RegressionCase(
            name="live-state verification",
            proposal=ActionProposal(
                name="observe the exact live prestate before mutation",
                advances_outcome=True,
                changes_state=False,
                produces_evidence=True,
            ),
            expected=Disposition.MOVE,
        ),
        RegressionCase(
            name="duplicate permission memo",
            proposal=ActionProposal(
                name="ask again after the required authority is already present",
                advances_outcome=True,
                changes_state=False,
            ),
            expected=Disposition.DROP,
        ),
        RegressionCase(
            name="passive stop after correction",
            proposal=ActionProposal(
                name="stop all safe work because the previous action was criticized",
                advances_outcome=False,
                changes_state=False,
            ),
            expected=Disposition.DROP,
        ),
        RegressionCase(
            name="stale sealed transaction",
            proposal=ActionProposal(
                name="execute from exact old receipts without checking current state",
                advances_outcome=True,
                changes_state=True,
                requires_current_state=True,
                current_state_verified=False,
            ),
            expected=Disposition.GATE,
        ),
        RegressionCase(
            name="unauthorized external mutation",
            proposal=ActionProposal(
                name="publish or merge without authority",
                advances_outcome=True,
                changes_state=True,
                reversible=False,
                boundaries=frozenset({Boundary.EXTERNAL}),
            ),
            expected=Disposition.GATE,
        ),
    )
