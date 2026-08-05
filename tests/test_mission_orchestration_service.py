from pathlib import Path

from forge.mission_orchestration.models import MissionStatus
from forge.mission_orchestration.service import MissionOrchestrationService
from forge.mission_orchestration.store import MissionCheckpointStore


def test_service_creates_deterministic_request(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_bytes(b"print('ok')\n")
    service = MissionOrchestrationService()

    first = service.create_request(
        repository_root=tmp_path,
        objective="Implement feature",
        requested_paths=("sample.py",),
    )
    second = service.create_request(
        repository_root=tmp_path,
        objective="Implement feature",
        requested_paths=("sample.py",),
    )

    assert first.mission_id == second.mission_id


def test_service_creates_ready_execution(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_bytes(b"print('ok')\n")
    service = MissionOrchestrationService()
    request = service.create_request(
        repository_root=tmp_path,
        objective="Implement feature",
        requested_paths=("sample.py",),
    )

    execution = service.create_execution(request)

    assert execution.status is MissionStatus.READY
    assert len(execution.workflow.stages) == 11


def test_service_checkpoints_execution(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_bytes(b"print('ok')\n")
    service = MissionOrchestrationService()
    request = service.create_request(
        repository_root=tmp_path,
        objective="Implement feature",
        requested_paths=("sample.py",),
    )
    execution = service.create_execution(request)
    store = MissionCheckpointStore(tmp_path / "checkpoints")

    checkpoint = service.checkpoint(execution, store)

    assert store.exists(request.mission_id)
    assert checkpoint.status is MissionStatus.READY