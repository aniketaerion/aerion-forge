import pytest
from pydantic import ValidationError

from forge.autonomous_decision.models import (
    CandidateAssessment,
    DecisionContext,
    DecisionRecord,
)
from forge.autonomous_decision.states import (
    CandidateRejectionReason,
    DecisionDisposition,
    DecisionKind,
)


def test_context_rejects_overlapping_step_states() -> None:
    with pytest.raises(ValidationError):
        DecisionContext(
            context_id="context-1",
            mission_id="mission-1",
            session_id="session-1",
            mission_state="executing",
            orchestration_state="ready",
            completed_step_ids=("step-1",),
            failed_step_ids=("step-1",),
            authority_level="a2_modify",
            approval_state="approved",
            repository_fingerprint="fingerprint-1",
            policy_version="1.0",
        )


def test_rejected_assessment_requires_reason() -> None:
    with pytest.raises(ValidationError):
        CandidateAssessment(
            assessment_id="assessment-1",
            candidate_id="candidate-1",
            feasible=False,
            policy_allowed=False,
            risk_score=0.5,
            confidence_score=0.5,
            evidence_score=0.5,
            utility_score=0.5,
            reversibility_score=0.5,
            total_score=0.0,
        )


def test_accepted_assessment_cannot_have_rejection_reason() -> None:
    with pytest.raises(ValidationError):
        CandidateAssessment(
            assessment_id="assessment-1",
            candidate_id="candidate-1",
            feasible=True,
            policy_allowed=True,
            risk_score=0.2,
            confidence_score=0.8,
            evidence_score=0.8,
            utility_score=0.7,
            reversibility_score=0.9,
            total_score=0.7,
            rejection_reasons=(
                CandidateRejectionReason.POLICY_VIOLATION,
            ),
        )


def test_select_action_requires_candidate() -> None:
    with pytest.raises(ValidationError):
        DecisionRecord(
            decision_id="decision-1",
            request_id="request-1",
            context_id="context-1",
            decision_kind=DecisionKind.NEXT_ACTION,
            disposition=DecisionDisposition.SELECT_ACTION,
            rationale="Select next action.",
            confidence=0.8,
            context_fingerprint="fingerprint-1",
        )


def test_no_safe_action_cannot_select_candidate() -> None:
    with pytest.raises(ValidationError):
        DecisionRecord(
            decision_id="decision-1",
            request_id="request-1",
            context_id="context-1",
            selected_candidate_id="candidate-1",
            decision_kind=DecisionKind.STOP,
            disposition=DecisionDisposition.NO_SAFE_ACTION,
            rationale="No candidate satisfies policy.",
            confidence=1.0,
            context_fingerprint="fingerprint-1",
        )