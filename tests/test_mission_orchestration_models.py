from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from forge.mission_orchestration.models import (
    ApprovalDecision,
    MissionApproval,
    MissionExecution,
    MissionRequest,
    MissionStatus,
    MissionWorkflow,
    StageDefinition,
    StageRun,
    StageStatus,
    StageType,
)


def request() -> MissionRequest:
    return MissionRequest(
        mission_id="mission-1",
        repository_root=".",
        objective="Implement bounded change",
        requested_paths=("forge/app.py",),
    )


def workflow() -> MissionWorkflow:
    validate = StageDefinition(
        stage_id="validate",
        stage_type=StageType.MISSION_VALIDATION,
        name="Validate mission",
    )
    plan = StageDefinition(
        stage_id="plan",
        stage_type=StageType.SAFE_CHANGE_PLAN,
        name="Plan safe change",
        dependencies=("validate",),
    )
    return MissionWorkflow(
        workflow_id="workflow-1",
        mission_id="mission-1",
        stages=(validate, plan),
    )


def test_request_rejects_path_traversal() -> None:
    with pytest.raises(ValidationError):
        MissionRequest(
            mission_id="mission-1",
            repository_root=".",
            objective="unsafe",
            requested_paths=("../secret.py",),
        )


def test_workflow_rejects_unknown_dependency() -> None:
    with pytest.raises(ValidationError):
        MissionWorkflow(
            workflow_id="workflow-1",
            mission_id="mission-1",
            stages=(
                StageDefinition(
                    stage_id="plan",
                    stage_type=StageType.SAFE_CHANGE_PLAN,
                    name="Plan",
                    dependencies=("missing",),
                ),
            ),
        )


def test_execution_rejects_mismatched_mission() -> None:
    with pytest.raises(ValidationError):
        MissionExecution(
            request=request(),
            workflow=MissionWorkflow(
                workflow_id="workflow-2",
                mission_id="different",
                stages=workflow().stages,
            ),
        )


def test_approval_requires_approver_identity() -> None:
    with pytest.raises(ValidationError):
        MissionApproval(decision=ApprovalDecision.APPROVED)


def test_models_are_immutable() -> None:
    item = StageRun(
        stage_run_id="run-1",
        stage_id="validate",
        attempt_number=1,
        status=StageStatus.RUNNING,
        started_at=datetime.now(UTC),
    )
    with pytest.raises(ValidationError):
        item.status = StageStatus.SUCCEEDED


def test_execution_accepts_known_current_stage() -> None:
    execution = MissionExecution(
        request=request(),
        workflow=workflow(),
        status=MissionStatus.RUNNING,
        current_stage_id="validate",
    )
    assert execution.current_stage_id == "validate"