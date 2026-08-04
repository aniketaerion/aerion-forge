from pathlib import Path

from forge.autonomous_repair.executor import repository_fingerprint
from forge.autonomous_repair.models import (
    RepairApproval,
    RepairExecutionStatus,
    RepairInput,
    RepairProviderType,
)
from forge.autonomous_repair.service import AutonomousRepairService


def repair_input(tmp_path: Path) -> RepairInput:
    return RepairInput(
        input_id="input-1",
        candidate_id="candidate-1",
        repository_root=str(tmp_path),
        provider=RepairProviderType.EXACT_PATCH,
        finding_ids=("f1",),
        target_paths=("sample.py",),
        repository_fingerprint=repository_fingerprint(
            tmp_path,
            ("sample.py",),
        ),
        objective="replace TODO",
    )


def test_service_proposes_and_dry_runs(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(b"TODO")

    service = AutonomousRepairService()
    proposal = service.propose(repair_input(tmp_path))
    request = service.build_request(
        proposal,
        repository_root=tmp_path,
        dry_run=True,
    )
    report = service.execute(request)

    assert report.status is RepairExecutionStatus.DRY_RUN_COMPLETE
    assert report.succeeded is False
    assert target.read_bytes() == b"TODO"


def test_service_applies_approved_repair(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(b"TODO")

    service = AutonomousRepairService()
    proposal = service.propose(repair_input(tmp_path))
    request = service.build_request(
        proposal,
        repository_root=tmp_path,
        dry_run=False,
        approval=RepairApproval(
            approved=True,
            approved_by="test-user",
            reason="approved test",
        ),
    )
    report = service.execute(
        request,
        validate=lambda _root, _proposal: True,
    )

    assert report.succeeded is True
    assert target.read_bytes() == b"DONE"


def test_service_persists_reports(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(b"TODO")

    service = AutonomousRepairService()
    proposal = service.propose(repair_input(tmp_path))
    request = service.build_request(
        proposal,
        repository_root=tmp_path,
        dry_run=True,
    )
    report = service.execute(request)
    written = service.write_reports(report, tmp_path / "reports")

    assert "AUTONOMOUS_REPAIR_SESSION.json" in written
    assert "AUTONOMOUS_REPAIR_REPORT.md" in written