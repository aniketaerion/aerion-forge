from pathlib import Path

import pytest

from forge.autonomous_repair.errors import (
    RepairRepositoryStateError,
    RepairValidationError,
)
from forge.autonomous_repair.executor import (
    AutonomousRepairExecutor,
    proposal_to_file_plans,
    repository_fingerprint,
)
from forge.autonomous_repair.models import (
    RepairApproval,
    RepairExecutionRequest,
    RepairExecutionStatus,
    RepairInput,
    RepairProposal,
    RepairProviderType,
)
from forge.autonomous_repair.policies import AutonomousRepairPolicy
from forge.autonomous_repair.providers.exact_patch import ExactPatchProvider


def proposal_for(tmp_path: Path) -> RepairProposal:
    repair_input = RepairInput(
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
    return ExactPatchProvider().propose(
        tmp_path,
        repair_input,
        AutonomousRepairPolicy(),
    )


def test_proposal_converts_to_safe_edit_plan(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_bytes(b"# TODO\n")
    plans = proposal_to_file_plans(proposal_for(tmp_path))

    assert len(plans) == 1
    assert plans[0].relative_path == "sample.py"
    assert plans[0].operations[0].expected_text == "TODO"


def test_dry_run_does_not_modify_repository(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(b"# TODO\n")
    proposal = proposal_for(tmp_path)
    request = RepairExecutionRequest(
        request_id="request-1",
        proposal=proposal,
        repository_root=str(tmp_path),
        repository_fingerprint=repository_fingerprint(
            tmp_path,
            proposal.affected_paths,
        ),
        dry_run=True,
    )

    attempt = AutonomousRepairExecutor().execute(request)

    assert attempt.status is RepairExecutionStatus.DRY_RUN_COMPLETE
    assert target.read_text(encoding="utf-8") == "# TODO\n"


def test_stale_repository_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(b"# TODO\n")
    proposal = proposal_for(tmp_path)
    fingerprint = repository_fingerprint(tmp_path, proposal.affected_paths)
    target.write_text("# changed\n", encoding="utf-8")
    request = RepairExecutionRequest(
        request_id="request-1",
        proposal=proposal,
        repository_root=str(tmp_path),
        repository_fingerprint=fingerprint,
        dry_run=True,
    )

    with pytest.raises(RepairRepositoryStateError):
        AutonomousRepairExecutor().execute(request)


def test_approved_apply_succeeds(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(b"TODO")
    proposal = proposal_for(tmp_path)
    request = RepairExecutionRequest(
        request_id="request-2",
        proposal=proposal,
        repository_root=str(tmp_path),
        repository_fingerprint=repository_fingerprint(
            tmp_path,
            proposal.affected_paths,
        ),
        dry_run=False,
        approval=RepairApproval(
            approved=True,
            approved_by="test-user",
            reason="test",
        ),
    )

    attempt = AutonomousRepairExecutor().execute(
        request,
        validate=lambda _root, _proposal: True,
    )

    assert attempt.status is RepairExecutionStatus.SUCCEEDED
    assert target.read_text(encoding="utf-8") == "DONE"


def test_failed_validation_rolls_back_full_file_replace(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(b"TODO")
    proposal = proposal_for(tmp_path)
    request = RepairExecutionRequest(
        request_id="request-3",
        proposal=proposal,
        repository_root=str(tmp_path),
        repository_fingerprint=repository_fingerprint(
            tmp_path,
            proposal.affected_paths,
        ),
        dry_run=False,
        approval=RepairApproval(
            approved=True,
            approved_by="test-user",
            reason="test rollback",
        ),
    )

    with pytest.raises(RepairValidationError):
        AutonomousRepairExecutor().execute(
            request,
            validate=lambda _root, _proposal: False,
        )

    assert target.read_text(encoding="utf-8") == "TODO"