from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionEvidenceKind,
    MissionResultStatus,
    MissionState,
)


def test_mission_state_values_are_stable() -> None:
    assert MissionState.PLANNING.value == "planning"
    assert (
        MissionState.AWAITING_PLAN_APPROVAL.value
        == "awaiting_plan_approval"
    )
    assert (
        MissionEvidenceKind.VERIFICATION.value
        == "verification"
    )
    assert (
        MissionApprovalDecision.APPROVED.value
        == "approved"
    )
    assert (
        MissionResultStatus.COMPLETED.value
        == "completed"
    )