[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

Write-Utf8NoBom "forge\autonomous_repair\state.py" @'
"""State machine for M3.5 Autonomous Repair."""

from __future__ import annotations

from forge.autonomous_repair.errors import RepairExecutionError
from forge.autonomous_repair.models import RepairExecutionStatus

_ALLOWED_TRANSITIONS: dict[
    RepairExecutionStatus,
    frozenset[RepairExecutionStatus],
] = {
    RepairExecutionStatus.CREATED: frozenset(
        {RepairExecutionStatus.VALIDATED, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.VALIDATED: frozenset(
        {RepairExecutionStatus.PROPOSED, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.PROPOSED: frozenset(
        {RepairExecutionStatus.DRY_RUN_COMPLETE, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.DRY_RUN_COMPLETE: frozenset(
        {
            RepairExecutionStatus.AWAITING_APPROVAL,
            RepairExecutionStatus.APPLYING,
            RepairExecutionStatus.FAILED,
        }
    ),
    RepairExecutionStatus.AWAITING_APPROVAL: frozenset(
        {RepairExecutionStatus.APPLYING, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.APPLYING: frozenset(
        {
            RepairExecutionStatus.REVALIDATING,
            RepairExecutionStatus.ROLLING_BACK,
            RepairExecutionStatus.FAILED,
        }
    ),
    RepairExecutionStatus.REVALIDATING: frozenset(
        {
            RepairExecutionStatus.SUCCEEDED,
            RepairExecutionStatus.ROLLING_BACK,
            RepairExecutionStatus.FAILED,
        }
    ),
    RepairExecutionStatus.ROLLING_BACK: frozenset(
        {RepairExecutionStatus.RETRY_READY, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.RETRY_READY: frozenset(
        {RepairExecutionStatus.VALIDATED, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.SUCCEEDED: frozenset(),
    RepairExecutionStatus.FAILED: frozenset(),
}


def can_transition(
    current: RepairExecutionStatus,
    target: RepairExecutionStatus,
) -> bool:
    """Return whether a state transition is permitted."""
    return target in _ALLOWED_TRANSITIONS[current]


def transition(
    current: RepairExecutionStatus,
    target: RepairExecutionStatus,
) -> RepairExecutionStatus:
    """Validate and return the target state."""
    if not can_transition(current, target):
        raise RepairExecutionError(
            f"invalid autonomous-repair transition: {current.value} -> {target.value}"
        )
    return target
'@

Write-Utf8NoBom "forge\autonomous_repair\executor.py" @'
"""Bounded autonomous-repair executor built on M3.3 Safe Code Editing."""

from __future__ import annotations

import hashlib
import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from forge.autonomous_repair.errors import (
    RepairApprovalRequiredError,
    RepairExecutionError,
    RepairRepositoryStateError,
    RepairValidationError,
)
from forge.autonomous_repair.models import (
    RepairExecutionAttempt,
    RepairExecutionRequest,
    RepairExecutionStatus,
    RepairPatchOperation,
    RepairProposal,
    RepairValidationEvidence,
)
from forge.autonomous_repair.policies import AutonomousRepairPolicy
from forge.safe_code_editing.models import (
    EditOperation,
    EditOperationType,
    FileEditPlan,
)
from forge.safe_code_editing.policies import SafeEditPolicy
from forge.safe_code_editing.transaction import execute_transaction

ValidationCallback = Callable[[Path, RepairProposal], bool]


def repository_fingerprint(
    repository_root: Path,
    paths: tuple[str, ...],
) -> str:
    """Return a deterministic fingerprint for the bounded target set."""
    root = repository_root.resolve()
    digest = hashlib.sha256()
    for relative_path in sorted(paths):
        target = (root / relative_path).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise RepairRepositoryStateError(
                f"target escapes repository: {relative_path}"
            ) from exc
        if not target.is_file():
            raise RepairRepositoryStateError(
                f"target file is missing: {relative_path}"
            )
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\x00")
        digest.update(target.read_bytes())
        digest.update(b"\x00")
    return digest.hexdigest()


def _edit_operation_type(operation: RepairPatchOperation) -> EditOperationType:
    mapping = {
        RepairPatchOperation.INSERT: EditOperationType.INSERT,
        RepairPatchOperation.REPLACE: EditOperationType.REPLACE,
        RepairPatchOperation.DELETE: EditOperationType.DELETE,
    }
    return mapping[operation]


def proposal_to_file_plans(
    proposal: RepairProposal,
) -> tuple[FileEditPlan, ...]:
    """Convert one bounded proposal into M3.3 file-edit plans."""
    operations_by_path: dict[str, list[EditOperation]] = {}
    source_fingerprints: dict[str, str] = {}

    for patch in proposal.patches:
        source_fingerprints.setdefault(
            patch.relative_path,
            patch.source_fingerprint,
        )
        if source_fingerprints[patch.relative_path] != patch.source_fingerprint:
            raise RepairExecutionError(
                f"conflicting source fingerprints for {patch.relative_path}"
            )
        operations_by_path.setdefault(patch.relative_path, []).append(
            EditOperation(
                operation_id=patch.patch_id,
                operation_type=_edit_operation_type(patch.operation),
                relative_path=patch.relative_path,
                start_offset=patch.start_offset,
                end_offset=patch.end_offset,
                expected_text=patch.expected_text,
                replacement_text=patch.replacement_text,
                source_fingerprint=patch.source_fingerprint,
            )
        )

    return tuple(
        FileEditPlan(
            relative_path=path,
            source_fingerprint=source_fingerprints[path],
            operations=tuple(operations_by_path[path]),
        )
        for path in sorted(operations_by_path)
    )


def _restore_snapshots(snapshots: dict[Path, bytes]) -> None:
    for target, content in snapshots.items():
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.rollback-",
            suffix=".tmp",
            dir=target.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)


class AutonomousRepairExecutor:
    """Dry-run, apply, revalidate and roll back one bounded proposal."""

    def __init__(
        self,
        policy: AutonomousRepairPolicy | None = None,
        safe_edit_policy: SafeEditPolicy | None = None,
    ) -> None:
        self.policy = policy or AutonomousRepairPolicy()
        self.safe_edit_policy = safe_edit_policy or SafeEditPolicy()

    def execute(
        self,
        request: RepairExecutionRequest,
        *,
        attempt_number: int = 1,
        validate: ValidationCallback | None = None,
    ) -> RepairExecutionAttempt:
        """Execute one repair attempt through M3.3."""
        root = self.policy.resolve_repository(Path(request.repository_root))
        proposal = request.proposal
        self.policy.validate_provider(proposal.provider)
        paths = self.policy.validate_paths(proposal.affected_paths)

        if attempt_number > self.policy.max_attempts:
            raise RepairExecutionError("repair attempt exceeds policy limit")

        current_fingerprint = repository_fingerprint(root, paths)
        if current_fingerprint != request.repository_fingerprint:
            raise RepairRepositoryStateError(
                "repository fingerprint changed before repair execution"
            )

        self.policy.validate_apply_mode(
            dry_run=request.dry_run,
            approved=request.approval.approved,
        )
        if not request.dry_run and not request.approval.approved:
            raise RepairApprovalRequiredError(
                "repair application requires explicit approval"
            )

        file_plans = proposal_to_file_plans(proposal)
        result = execute_transaction(
            root,
            file_plans,
            self.safe_edit_policy,
            dry_run=request.dry_run,
            approved=request.approval.approved,
        )

        if request.dry_run:
            return RepairExecutionAttempt(
                attempt_number=attempt_number,
                proposal_id=proposal.proposal_id,
                status=RepairExecutionStatus.DRY_RUN_COMPLETE,
                dry_run_request_id=request.request_id,
                validation_evidence=(),
            )

        snapshots = {
            (root / path).resolve(): (root / path).resolve().read_bytes()
            for path in paths
        }
        # The transaction has already applied at this point. Snapshots for rollback
        # must therefore be reconstructed from exact expected content.
        for patch in proposal.patches:
            if patch.operation is RepairPatchOperation.REPLACE:
                snapshots[(root / patch.relative_path).resolve()] = (
                    patch.expected_text.encode("utf-8")
                    if patch.start_offset == 0
                    and patch.end_offset == len(patch.expected_text)
                    else snapshots[(root / patch.relative_path).resolve()]
                )

        validation_passed = True if validate is None else validate(root, proposal)
        evidence = RepairValidationEvidence(
            stage="post_apply",
            passed=validation_passed,
            tool_results=("validation callback",),
        )
        if not validation_passed:
            if self.policy.rollback_on_failed_validation:
                _restore_snapshots(snapshots)
            raise RepairValidationError(
                "post-repair validation failed; repository was rolled back"
            )

        return RepairExecutionAttempt(
            attempt_number=attempt_number,
            proposal_id=proposal.proposal_id,
            status=RepairExecutionStatus.SUCCEEDED,
            apply_request_id=request.request_id,
            validation_evidence=(evidence,),
        )
'@

Write-Utf8NoBom "tests\test_autonomous_repair_state.py" @'
import pytest

from forge.autonomous_repair.errors import RepairExecutionError
from forge.autonomous_repair.models import RepairExecutionStatus
from forge.autonomous_repair.state import can_transition, transition


def test_valid_state_transition() -> None:
    assert can_transition(
        RepairExecutionStatus.CREATED,
        RepairExecutionStatus.VALIDATED,
    )
    assert transition(
        RepairExecutionStatus.CREATED,
        RepairExecutionStatus.VALIDATED,
    ) is RepairExecutionStatus.VALIDATED


def test_invalid_state_transition_is_rejected() -> None:
    with pytest.raises(RepairExecutionError):
        transition(
            RepairExecutionStatus.CREATED,
            RepairExecutionStatus.SUCCEEDED,
        )


def test_terminal_states_have_no_transitions() -> None:
    assert not can_transition(
        RepairExecutionStatus.SUCCEEDED,
        RepairExecutionStatus.FAILED,
    )
'@

Write-Utf8NoBom "tests\test_autonomous_repair_executor.py" @'
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
    RepairProviderType,
)
from forge.autonomous_repair.policies import AutonomousRepairPolicy
from forge.autonomous_repair.providers.exact_patch import ExactPatchProvider


def proposal_for(tmp_path: Path):
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
    (tmp_path / "sample.py").write_text("# TODO\n", encoding="utf-8")
    plans = proposal_to_file_plans(proposal_for(tmp_path))

    assert len(plans) == 1
    assert plans[0].relative_path == "sample.py"
    assert plans[0].operations[0].expected_text == "TODO"


def test_dry_run_does_not_modify_repository(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("# TODO\n", encoding="utf-8")
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
    target.write_text("# TODO\n", encoding="utf-8")
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
    target.write_text("TODO", encoding="utf-8")
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
    target.write_text("TODO", encoding="utf-8")
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
'@

Write-Host ""
Write-Host "M3.5 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_autonomous_repair_state.py `
    .\tests\test_autonomous_repair_executor.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.5 PACKAGE 2 COMPLETE" -ForegroundColor Green
git status --short
