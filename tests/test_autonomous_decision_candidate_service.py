from forge.autonomous_decision.candidate_service import (
    CandidatePreparationService,
)
from forge.autonomous_decision.models import (
    DecisionContext,
    DecisionRequest,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)


def test_candidate_service_prepares_candidates() -> None:
    service = CandidatePreparationService(
        policy=AutonomousDecisionPolicy()
    )
    request = DecisionRequest(
        request_id="request-1",
        mission_id="mission-1",
        session_id="session-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        requested_by="Aerion",
    )
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="step_selecting",
        current_step_id="step-1",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=("evidence-1",),
        policy_version="1.0",
    )

    result = service.prepare(request, context)

    assert result.prepared
    assert result.accepted
    assert all(
        item.rejection_reasons == ()
        for item in result.accepted
    )