from datetime import timedelta

from forge.autonomous_runtime.models import (
    ApprovalDecision,
    AutonomousMission,
    MissionRequest,
    utc_now,
)
from forge.autonomous_runtime.permission import decide_permission
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    RiskClass,
)


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Evaluate permission.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A4_COMMIT,
            requested_by="Aerion",
        ),
        granted_authority=AuthorityLevel.A4_COMMIT,
    )


def test_high_risk_action_is_denied_without_approval() -> None:
    decision = decide_permission(
        mission(),
        required_authority=AuthorityLevel.A4_COMMIT,
        risk_class=RiskClass.R4_CRITICAL,
        scope=("forge/autonomous_runtime",),
        action_kind="create_commit",
    )

    assert not decision.permitted
    assert decision.approval_required


def test_valid_approval_permits_high_risk_action() -> None:
    item = ApprovalDecision(
        approval_id="approval-1",
        mission_id="mission-1",
        decision="approve",
        authority_granted=AuthorityLevel.A4_COMMIT,
        scope=("forge/autonomous_runtime",),
        approved_by="Aerion",
        expires_at=utc_now() + timedelta(minutes=5),
    )

    decision = decide_permission(
        mission(),
        required_authority=AuthorityLevel.A4_COMMIT,
        risk_class=RiskClass.R4_CRITICAL,
        scope=("forge/autonomous_runtime",),
        action_kind="create_commit",
        approval=item,
    )

    assert decision.permitted
    assert decision.approval_required