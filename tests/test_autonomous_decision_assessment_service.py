from forge.autonomous_decision.assessment_service import (
    CandidateAssessmentService,
)
from forge.autonomous_decision.candidate_service import (
    PreparedCandidate,
)
from forge.autonomous_decision.feasibility import (
    FeasibilityResult,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.policy_filter import (
    PolicyFilterResult,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
)


def test_assessment_service_accepts_supported_candidate() -> None:
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.EXECUTE_NEXT_STEP,
        target_step_id="step-1",
        description="Execute step.",
        required_authority="a2_modify",
        risk_class="medium",
        expected_effects=("Step completed.",),
        evidence_references=(
            "evidence-1",
            "evidence-2",
            "evidence-3",
        ),
        source=CandidateSource.APPROVED_PLAN,
    )
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        current_step_id="step-1",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=(
            "evidence-1",
            "evidence-2",
            "evidence-3",
        ),
        policy_version="1.0",
    )
    prepared = PreparedCandidate(
        candidate=candidate,
        feasibility=FeasibilityResult(
            feasible=True,
            rejection_reasons=(),
        ),
        policy=PolicyFilterResult(
            allowed=True,
            rejection_reasons=(),
        ),
    )

    result = CandidateAssessmentService(
        policy=AutonomousDecisionPolicy()
    ).assess(prepared, context)

    assert result.feasible
    assert result.policy_allowed
    assert result.rejection_reasons == ()
    assert result.total_score > 0.0