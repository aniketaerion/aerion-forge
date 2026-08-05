from pathlib import Path

import pytest

from forge.mission_orchestration.errors import (
    MissionCancellationError,
    MissionRecoveryError,
)
from forge.mission_orchestration.models import (
    MissionExecution,
    MissionStatus,
)
from forge.mission_orchestration.recovery import MissionRecoveryService
from forge.mission_orchestration.service import MissionOrchestrationService
from forge.mission_orchestration.store import MissionCheckpointStore


def execution_for(tmp_path: Path) -> tuple[MissionOrchestrationService, MissionExecution]:
    (tmp_path / "sample.py").write_bytes(b"print('ok')\n")
    service = MissionOrchestrationService()
    request = service.create_request(
        repository_root=tmp_path,
        objective="Recover mission",
        requested_paths=("sample.py",),
    )
    return service, service.create_execution(request)


def test_resume_restores_checkpoint_state(tmp_path: Path) -> None:
    service, execution = execution_for(tmp_path)
    execution = service.run_next(execution)
    checkpoint = service.checkpoint(
        execution,
        MissionCheckpointStore(tmp_path / "checkpoints"),
    )

    resumed = MissionRecoveryService().resume(execution, checkpoint)

    assert resumed.status is MissionStatus.RESUMING
    assert resumed.stage_runs == checkpoint.stage_runs
    assert resumed.checkpoint_id == checkpoint.checkpoint_id


def test_resume_rejects_repository_drift(tmp_path: Path) -> None:
    service, execution = execution_for(tmp_path)
    checkpoint = service.checkpoint(
        execution,
        MissionCheckpointStore(tmp_path / "checkpoints"),
    )
    (tmp_path / "sample.py").write_bytes(b"print('changed')\n")

    with pytest.raises(MissionRecoveryError):
        MissionRecoveryService().resume(execution, checkpoint)


def test_cancel_requires_reason(tmp_path: Path) -> None:
    _, execution = execution_for(tmp_path)

    with pytest.raises(MissionCancellationError):
        MissionRecoveryService().cancel(execution, reason="")


def test_cancel_marks_execution_cancelled(tmp_path: Path) -> None:
    _, execution = execution_for(tmp_path)

    cancelled = MissionRecoveryService().cancel(
        execution,
        reason="operator requested cancellation",
    )

    assert cancelled.status is MissionStatus.CANCELLED
    assert cancelled.failure_reason == "operator requested cancellation"