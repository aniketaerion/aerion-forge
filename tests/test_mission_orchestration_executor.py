from pathlib import Path

from forge.mission_orchestration.executor import MissionExecutor
from forge.mission_orchestration.models import (
    ApprovalDecision,
    MissionApproval,
    MissionExecution,
    MissionStatus,
)
from forge.mission_orchestration.service import MissionOrchestrationService


def execution_for(tmp_path: Path) -> MissionExecution:
    (tmp_path / "sample.py").write_bytes(b"print('ok')\n")
    service = MissionOrchestrationService()
    request = service.create_request(
        repository_root=tmp_path,
        objective="Run mission",
        requested_paths=("sample.py",),
    )
    return service.create_execution(request)


def test_executor_runs_first_ready_stage(tmp_path: Path) -> None:
    execution = execution_for(tmp_path)

    updated = MissionExecutor().execute_next(execution)

    assert updated.stage_runs[0].stage_id == "mission_validation"
    assert updated.stage_runs[0].status.value == "succeeded"


def test_executor_blocks_approval_stage(tmp_path: Path) -> None:
    execution = execution_for(tmp_path)
    executor = MissionExecutor()

    for _ in range(4):
        execution = executor.execute_next(execution)

    blocked = executor.execute_next(execution)

    assert blocked.status is MissionStatus.AWAITING_APPROVAL
    assert blocked.current_stage_id == "approval_gate"


def test_executor_accepts_approval(tmp_path: Path) -> None:
    execution = execution_for(tmp_path)
    executor = MissionExecutor()

    for _ in range(4):
        execution = executor.execute_next(execution)

    execution = executor.execute_next(execution)
    approved = executor.execute_next(
        execution,
        approval=MissionApproval(
            decision=ApprovalDecision.APPROVED,
            approved_by="test-user",
            reason="approved",
        ),
    )

    assert approved.stage_runs[-1].stage_id == "approval_gate"
    assert approved.stage_runs[-1].status.value == "succeeded"
