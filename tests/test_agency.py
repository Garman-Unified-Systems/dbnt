"""Regression tests for DBNT bounded-agency action selection."""

from click.testing import CliRunner

from dbnt.agency import (
    ActionProposal,
    ActionRejectedError,
    Boundary,
    Disposition,
    Effect,
    RegressionCase,
    classify_action,
    default_regression_cases,
    evaluate_cases,
)
from dbnt.cli import main


def test_safe_reversible_in_scope_work_moves():
    decision = classify_action(
        ActionProposal(
            name="fix a local parser with tests",
            advances_outcome=True,
            effect=Effect.LOCAL_MUTATION,
        )
    )

    assert decision.disposition is Disposition.MOVE
    assert decision.unmet_boundaries == ()


def test_read_only_live_state_check_moves_when_it_produces_evidence():
    decision = classify_action(
        ActionProposal(
            name="verify the deployed process",
            advances_outcome=True,
            effect=Effect.OBSERVE,
            produces_evidence=True,
        )
    )

    assert decision.disposition is Disposition.MOVE


def test_ceremony_without_state_change_or_evidence_drops():
    decision = classify_action(
        ActionProposal(
            name="write another plan for an already clear fix",
            advances_outcome=True,
            effect=Effect.OBSERVE,
            produces_evidence=False,
        )
    )

    assert decision.disposition is Disposition.DROP
    assert "state change" in decision.reasons[0]


def test_out_of_scope_action_gates_once():
    decision = classify_action(
        ActionProposal(
            name="change an unrelated service",
            advances_outcome=True,
            effect=Effect.LOCAL_MUTATION,
            in_scope=False,
        )
    )

    assert decision.disposition is Disposition.GATE
    assert decision.unmet_boundaries == (Boundary.SCOPE,)


def test_external_irreversible_action_requires_explicit_authority():
    decision = classify_action(
        ActionProposal(
            name="merge and deploy",
            advances_outcome=True,
            effect=Effect.EXTERNAL_MUTATION,
            reversible=False,
        )
    )

    assert decision.disposition is Disposition.GATE
    assert decision.unmet_boundaries == (
        Boundary.EXTERNAL,
        Boundary.IRREVERSIBLE,
        Boundary.AUTHORITY,
    )


def test_external_effect_derives_authority_even_if_caller_omits_boundaries():
    decision = classify_action(
        ActionProposal(
            name="publish",
            advances_outcome=True,
            effect=Effect.EXTERNAL_MUTATION,
        )
    )

    assert decision.disposition is Disposition.GATE
    assert decision.unmet_boundaries == (
        Boundary.EXTERNAL,
        Boundary.AUTHORITY,
    )


def test_boundary_grants_cannot_substitute_for_verified_authority():
    boundaries = frozenset({Boundary.EXTERNAL, Boundary.IRREVERSIBLE})
    decision = classify_action(
        ActionProposal(
            name="execute an already authorized exact merge",
            advances_outcome=True,
            effect=Effect.EXTERNAL_MUTATION,
            reversible=False,
            authorized_boundaries=boundaries,
        )
    )

    assert decision.disposition is Disposition.GATE
    assert decision.unmet_boundaries == (Boundary.AUTHORITY,)


def test_verified_exact_authority_allows_external_execution():
    boundaries = frozenset({Boundary.EXTERNAL, Boundary.IRREVERSIBLE})
    decision = classify_action(
        ActionProposal(
            name="execute an already authorized exact merge",
            advances_outcome=True,
            effect=Effect.EXTERNAL_MUTATION,
            reversible=False,
            authorized_boundaries=boundaries,
            authority_verified=True,
        )
    )

    assert decision.disposition is Disposition.MOVE
    assert decision.unmet_boundaries == ()


def test_stale_artifact_cannot_substitute_for_current_state():
    decision = classify_action(
        ActionProposal(
            name="execute a sealed but temporally stale promotion",
            advances_outcome=True,
            effect=Effect.LOCAL_MUTATION,
            requires_current_state=True,
            current_state_verified=False,
        )
    )

    assert decision.disposition is Disposition.GATE
    assert decision.unmet_boundaries == (Boundary.CURRENT_STATE,)


def test_privacy_and_credentials_remain_real_boundaries():
    decision = classify_action(
        ActionProposal(
            name="move a credential-bearing home dataset",
            advances_outcome=True,
            effect=Effect.LOCAL_MUTATION,
            boundaries=frozenset({Boundary.CREDENTIAL, Boundary.PRIVACY}),
        )
    )

    assert decision.disposition is Disposition.GATE
    assert decision.unmet_boundaries == (
        Boundary.CREDENTIAL,
        Boundary.PRIVACY,
        Boundary.AUTHORITY,
    )


def test_default_regression_suite_encodes_the_oscillation_failures():
    cases = default_regression_cases()
    names = {case.name for case in cases}

    assert {
        "safe bounded fix",
        "live-state verification",
        "duplicate permission memo",
        "passive stop after correction",
        "stale sealed transaction",
        "unauthorized external mutation",
    } <= names
    assert evaluate_cases(cases).passed


def test_evaluator_names_policy_regressions():
    case = RegressionCase(
        name="wrong expectation",
        proposal=ActionProposal(
            name="local reversible fix",
            advances_outcome=True,
            effect=Effect.LOCAL_MUTATION,
        ),
        expected=Disposition.GATE,
    )

    result = evaluate_cases([case])

    assert not result.passed
    assert result.total == 1
    assert result.passing == 0
    assert result.failures[0].case_name == "wrong expectation"
    assert result.failures[0].actual is Disposition.MOVE


def test_agency_check_cli_runs_the_baseline_regressions():
    result = CliRunner().invoke(main, ["agency-check"])

    assert result.exit_code == 0
    assert "Bounded agency: PASS" in result.output
    assert "6/6 regression cases" in result.output


def test_agency_decide_cli_fail_closes_external_action_without_authority():
    result = CliRunner().invoke(
        main,
        [
            "agency-decide",
            "--name",
            "publish",
            "--effect",
            "external_mutation",
        ],
    )

    assert result.exit_code == 2
    assert '"disposition": "gate"' in result.output
    assert '"authority"' in result.output


def test_action_rejected_carries_the_full_decision():
    proposal = ActionProposal(
        name="publish",
        advances_outcome=True,
        effect=Effect.EXTERNAL_MUTATION,
    )

    error = ActionRejectedError(classify_action(proposal))

    assert error.decision.disposition is Disposition.GATE
