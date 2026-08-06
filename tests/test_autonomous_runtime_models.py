from datetime import timedelta

import pytest
from pydantic import ValidationError

from forge.autonomous_runtime.models import (
    ApprovalDecision,
    AutonomousMission,
    MissionOutcome,
    MissionRequest,
    MissionStep,
    utc_now,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
    ReviewDecision,
)


def request() -> MissionRequest:
    return MissionRequest(
        request_id="request-1",
        objective="Implement autonomous runtime contracts.",
        repository_root="D:/Software Dev/Aerion Forge",
        requested_scope=("forge/autonomous_runtime",),
        excluded_scope=("deployments",),
        acceptance_criteria=("All tests pass.",),
        requested_authority=AuthorityLevel.A2_MODIFY,
        requested_by="Aerion",
    )


def test_contracts_are_immutable() -> None:
    mission_request = request()

    with pytest.raises(ValidationError):
        mission_request.objective = "Changed"


def test_scope_overlap_is_rejected() -> None:
    with pytest.raises(ValidationError):
        MissionRequest(
            request_id="request-2",
            objective="Invalid scope.",
            repository_root="repository",
            requested_scope=("forge",),
            excluded_scope=("forge",),
            requested_by="Aerion",
        )


def test_modifying_step_requires_checkpoint() -> None:
    with pytest.raises(ValidationError):
        MissionStep(
            step_id="step-1",
            plan_id="plan-1",
            sequence=1,
            title="Modify code",
            description="Modify approved code.",
            action_kind="apply_patch",
            required_authority=AuthorityLevel.A2_MODIFY,
            checkpoint_required=False,
        )


def test_terminal_mission_requires_outcome() -> None:
    with pytest.raises(ValidationError):
        AutonomousMission(
            mission_id="mission-1",
            request=request(),
            state=MissionState.COMPLETED,
            granted_authority=AuthorityLevel.A2_MODIFY,
        )


def test_completed_outcome_requires_approved_review() -> None:
    with pytest.raises(ValidationError):
        MissionOutcome(
            outcome_id="outcome-1",
            mission_id="mission-1",
            terminal_state=MissionState.COMPLETED,
            objective_satisfied=True,
            review_decision=ReviewDecision.REJECT,
        )


def test_approval_activity_uses_expiry_and_revocation() -> None:
    active = ApprovalDecision(
        approval_id="approval-1",
        mission_id="mission-1",
        decision="approve",
        authority_granted=AuthorityLevel.A2_MODIFY,
        approved_by="Aerion",
        expires_at=utc_now() + timedelta(minutes=5),
    )
    expired = ApprovalDecision(
        approval_id="approval-2",
        mission_id="mission-1",
        decision="approve",
        authority_granted=AuthorityLevel.A2_MODIFY,
        approved_by="Aerion",
        expires_at=utc_now() - timedelta(minutes=5),
    )

    assert active.active
    assert not expired.active