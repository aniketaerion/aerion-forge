from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.policy_filter import (
    evaluate_candidate_policy,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateRejectionReason,
    CandidateSource,
)


def context() -> DecisionContext:
    return DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=("evidence-1",),
        policy_version="1.0",
    )


def test_high_risk_candidate_is_rejected() -> None:
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.ROLLBACK_CURRENT_STEP,
        target_step_id="step-1",
        description="Rollback step.",
        required_authority="a2_modify",
        approval_required=False,
        risk_class="high",
        evidence_references=("evidence-1",),
        source=CandidateSource.RECOVERY_POLICY,
    )

    result = evaluate_candidate_policy(
        candidate,
        context(),
        AutonomousDecisionPolicy(),
    )

    assert not result.allowed
    assert (
        CandidateRejectionReason.RISK_THRESHOLD_EXCEEDED
        in result.rejection_reasons
    )


def test_candidate_without_evidence_is_rejected() -> None:
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.PAUSE_MISSION,
        description="Pause mission.",
        required_authority="a2_modify",
        risk_class="low",
        source=CandidateSource.ORCHESTRATION_STATE,
    )

    result = evaluate_candidate_policy(
        candidate,
        context(),
        AutonomousDecisionPolicy(),
    )

    assert (
        CandidateRejectionReason.EVIDENCE_INSUFFICIENT
        in result.rejection_reasons
    )