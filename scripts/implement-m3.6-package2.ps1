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

Write-Utf8NoBom "forge\mission_orchestration\store.py" @'
"""Checkpoint persistence for M3.6 Mission Orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from forge.mission_orchestration.errors import MissionCheckpointError
from forge.mission_orchestration.models import MissionCheckpoint


class MissionCheckpointStore:
    """Persist and load immutable mission checkpoints."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def _path(self, mission_id: str) -> Path:
        return self.root / f"{mission_id}.json"

    def save(self, checkpoint: MissionCheckpoint) -> Path:
        """Atomically persist one checkpoint."""
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            target = self._path(checkpoint.mission_id)
            temporary = target.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(
                    checkpoint.model_dump(mode="json"),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            temporary.replace(target)
            return target
        except OSError as exc:
            raise MissionCheckpointError(
                f"unable to save mission checkpoint: {exc}"
            ) from exc

    def load(self, mission_id: str) -> MissionCheckpoint:
        """Load one checkpoint by mission ID."""
        path = self._path(mission_id)
        try:
            return MissionCheckpoint.model_validate_json(
                path.read_text(encoding="utf-8-sig")
            )
        except (OSError, ValidationError) as exc:
            raise MissionCheckpointError(
                f"unable to load mission checkpoint {mission_id}: {exc}"
            ) from exc

    def exists(self, mission_id: str) -> bool:
        """Return whether a checkpoint exists."""
        return self._path(mission_id).is_file()

    def list_missions(self) -> tuple[str, ...]:
        """Return persisted mission IDs deterministically."""
        if not self.root.is_dir():
            return ()
        return tuple(sorted(path.stem for path in self.root.glob("*.json")))
'@

Write-Utf8NoBom "forge\mission_orchestration\executor.py" @'
"""Deterministic stage execution for M3.6 Mission Orchestration."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from forge.mission_orchestration.errors import (
    MissionDependencyError,
    MissionExecutionError,
    MissionPolicyViolationError,
)
from forge.mission_orchestration.identifiers import stage_run_identifier
from forge.mission_orchestration.models import (
    MissionApproval,
    MissionExecution,
    MissionStatus,
    StageDefinition,
    StageResult,
    StageRun,
    StageStatus,
)
from forge.mission_orchestration.policies import MissionOrchestrationPolicy

StageHandler = Callable[[MissionExecution, StageDefinition], StageResult]


class MissionExecutor:
    """Execute one deterministic workflow stage at a time."""

    def __init__(
        self,
        *,
        policy: MissionOrchestrationPolicy | None = None,
        handlers: dict[str, StageHandler] | None = None,
    ) -> None:
        self.policy = policy or MissionOrchestrationPolicy()
        self.handlers = handlers or {}

    def _successful_stage_ids(
        self,
        execution: MissionExecution,
    ) -> set[str]:
        return {
            run.stage_id
            for run in execution.stage_runs
            if run.status in {StageStatus.SUCCEEDED, StageStatus.SKIPPED}
        }

    def next_stage(
        self,
        execution: MissionExecution,
    ) -> StageDefinition | None:
        """Return the next dependency-ready stage."""
        completed = self._successful_stage_ids(execution)

        for stage in execution.workflow.stages:
            if stage.stage_id in completed:
                continue
            if set(stage.dependencies).issubset(completed):
                return stage
        return None

    def execute_next(
        self,
        execution: MissionExecution,
        *,
        approval: MissionApproval | None = None,
    ) -> MissionExecution:
        """Execute the next ready stage and return updated mission state."""
        if len(execution.stage_runs) >= self.policy.max_total_stage_runs:
            raise MissionPolicyViolationError(
                "mission exceeded maximum total stage runs"
            )

        stage = self.next_stage(execution)
        if stage is None:
            return execution.model_copy(
                update={
                    "status": MissionStatus.COMPLETED,
                    "current_stage_id": None,
                }
            )

        attempts = 1 + sum(
            1 for run in execution.stage_runs if run.stage_id == stage.stage_id
        )
        self.policy.validate_stage_attempts(attempts)
        if attempts > stage.max_attempts:
            raise MissionPolicyViolationError(
                f"stage exceeded max attempts: {stage.stage_id}"
            )

        approval_evidence = approval or MissionApproval()
        if stage.approval_required and approval_evidence.decision.value != "approved":
            run = StageRun(
                stage_run_id=stage_run_identifier(
                    {
                        "mission_id": execution.request.mission_id,
                        "stage_id": stage.stage_id,
                        "attempt": attempts,
                        "status": StageStatus.AWAITING_APPROVAL.value,
                    }
                ),
                stage_id=stage.stage_id,
                attempt_number=attempts,
                status=StageStatus.AWAITING_APPROVAL,
                approval=approval_evidence,
            )
            return execution.model_copy(
                update={
                    "status": MissionStatus.AWAITING_APPROVAL,
                    "current_stage_id": stage.stage_id,
                    "stage_runs": execution.stage_runs + (run,),
                }
            )

        started = datetime.now(UTC)
        handler = self.handlers.get(stage.stage_id)
        if handler is None:
            result = StageResult(
                messages=(f"Stage completed: {stage.stage_id}",)
            )
        else:
            try:
                result = handler(execution, stage)
            except Exception as exc:
                failed = StageRun(
                    stage_run_id=stage_run_identifier(
                        {
                            "mission_id": execution.request.mission_id,
                            "stage_id": stage.stage_id,
                            "attempt": attempts,
                            "status": StageStatus.FAILED.value,
                        }
                    ),
                    stage_id=stage.stage_id,
                    attempt_number=attempts,
                    status=StageStatus.FAILED,
                    started_at=started,
                    completed_at=datetime.now(UTC),
                    approval=approval_evidence,
                    errors=(str(exc),),
                )
                raise MissionExecutionError(
                    f"stage failed: {stage.stage_id}: {exc}"
                ) from exc

        run = StageRun(
            stage_run_id=stage_run_identifier(
                {
                    "mission_id": execution.request.mission_id,
                    "stage_id": stage.stage_id,
                    "attempt": attempts,
                    "status": StageStatus.SUCCEEDED.value,
                }
            ),
            stage_id=stage.stage_id,
            attempt_number=attempts,
            status=StageStatus.SUCCEEDED,
            started_at=started,
            completed_at=datetime.now(UTC),
            approval=approval_evidence,
            result=result,
        )
        updated = execution.model_copy(
            update={
                "status": MissionStatus.RUNNING,
                "current_stage_id": stage.stage_id,
                "stage_runs": execution.stage_runs + (run,),
            }
        )

        if self.next_stage(updated) is None:
            return updated.model_copy(
                update={
                    "status": MissionStatus.COMPLETED,
                    "current_stage_id": None,
                }
            )
        return updated

    def validate_dependencies(self, execution: MissionExecution) -> None:
        """Reject stage runs that violate dependency ordering."""
        completed: set[str] = set()
        by_id = {
            stage.stage_id: stage
            for stage in execution.workflow.stages
        }

        for run in execution.stage_runs:
            try:
                stage = by_id[run.stage_id]
            except KeyError as exc:
                raise MissionDependencyError(
                    f"unknown stage run: {run.stage_id}"
                ) from exc
            if not set(stage.dependencies).issubset(completed):
                raise MissionDependencyError(
                    f"stage ran before dependencies: {stage.stage_id}"
                )
            if run.status in {StageStatus.SUCCEEDED, StageStatus.SKIPPED}:
                completed.add(run.stage_id)
'@

Write-Utf8NoBom "forge\mission_orchestration\service.py" @'
"""Mission orchestration service for M3.6."""

from __future__ import annotations

import hashlib
from pathlib import Path

from forge.mission_orchestration.identifiers import (
    checkpoint_identifier,
    mission_identifier,
)
from forge.mission_orchestration.models import (
    MissionApproval,
    MissionCheckpoint,
    MissionExecution,
    MissionRequest,
    MissionStatus,
)
from forge.mission_orchestration.policies import MissionOrchestrationPolicy
from forge.mission_orchestration.executor import MissionExecutor
from forge.mission_orchestration.store import MissionCheckpointStore
from forge.mission_orchestration.workflow import build_default_workflow


def repository_fingerprint(
    repository_root: Path,
    paths: tuple[str, ...],
) -> str:
    """Fingerprint only the mission's bounded target paths."""
    root = repository_root.resolve()
    digest = hashlib.sha256()

    for relative_path in sorted(paths):
        target = (root / relative_path).resolve()
        target.relative_to(root)
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\x00")
        if target.is_file():
            digest.update(target.read_bytes())
        digest.update(b"\x00")
    return digest.hexdigest()


class MissionOrchestrationService:
    """Create, execute and checkpoint engineering missions."""

    def __init__(
        self,
        *,
        policy: MissionOrchestrationPolicy | None = None,
        executor: MissionExecutor | None = None,
    ) -> None:
        self.policy = policy or MissionOrchestrationPolicy()
        self.executor = executor or MissionExecutor(policy=self.policy)

    def create_request(
        self,
        *,
        repository_root: Path,
        objective: str,
        requested_paths: tuple[str, ...],
        constraints: tuple[str, ...] = (),
        requested_outcomes: tuple[str, ...] = (),
    ) -> MissionRequest:
        """Create a deterministic bounded mission request."""
        root = self.policy.resolve_repository(repository_root)
        normalized = self.policy.validate_paths(requested_paths)
        mission_id = mission_identifier(
            {
                "repository_root": str(root),
                "objective": objective,
                "requested_paths": normalized,
                "constraints": constraints,
                "requested_outcomes": requested_outcomes,
            }
        )
        return MissionRequest(
            mission_id=mission_id,
            repository_root=str(root),
            objective=objective,
            requested_paths=normalized,
            constraints=constraints,
            requested_outcomes=requested_outcomes,
        )

    def create_execution(
        self,
        request: MissionRequest,
    ) -> MissionExecution:
        """Create a validated mission execution."""
        workflow = build_default_workflow(
            request,
            policy=self.policy,
        )
        return MissionExecution(
            request=request,
            workflow=workflow,
            status=MissionStatus.READY,
        )

    def run_next(
        self,
        execution: MissionExecution,
        *,
        approval: MissionApproval | None = None,
    ) -> MissionExecution:
        """Execute exactly one workflow stage."""
        return self.executor.execute_next(
            execution,
            approval=approval,
        )

    def checkpoint(
        self,
        execution: MissionExecution,
        store: MissionCheckpointStore,
    ) -> MissionCheckpoint:
        """Persist one resumable checkpoint."""
        fingerprint = repository_fingerprint(
            Path(execution.request.repository_root),
            execution.request.requested_paths,
        )
        checkpoint = MissionCheckpoint(
            checkpoint_id=checkpoint_identifier(
                {
                    "mission_id": execution.request.mission_id,
                    "workflow_id": execution.workflow.workflow_id,
                    "status": execution.status.value,
                    "stage_run_ids": [
                        run.stage_run_id for run in execution.stage_runs
                    ],
                    "repository_fingerprint": fingerprint,
                }
            ),
            mission_id=execution.request.mission_id,
            workflow_id=execution.workflow.workflow_id,
            status=execution.status,
            stage_runs=execution.stage_runs,
            current_stage_id=execution.current_stage_id,
            repository_fingerprint=fingerprint,
        )
        store.save(checkpoint)
        return checkpoint
'@

Write-Utf8NoBom "tests\test_mission_orchestration_store.py" @'
from pathlib import Path

from forge.mission_orchestration.models import (
    MissionCheckpoint,
    MissionStatus,
)
from forge.mission_orchestration.store import MissionCheckpointStore


def test_store_round_trip(tmp_path: Path) -> None:
    store = MissionCheckpointStore(tmp_path)
    checkpoint = MissionCheckpoint(
        checkpoint_id="checkpoint-1",
        mission_id="mission-1",
        workflow_id="workflow-1",
        status=MissionStatus.READY,
        repository_fingerprint="a" * 64,
    )

    store.save(checkpoint)
    loaded = store.load("mission-1")

    assert loaded == checkpoint
    assert store.exists("mission-1")


def test_store_lists_missions_deterministically(tmp_path: Path) -> None:
    store = MissionCheckpointStore(tmp_path)
    for mission_id in ("mission-b", "mission-a"):
        store.save(
            MissionCheckpoint(
                checkpoint_id=f"checkpoint-{mission_id}",
                mission_id=mission_id,
                workflow_id="workflow-1",
                status=MissionStatus.READY,
                repository_fingerprint="a" * 64,
            )
        )

    assert store.list_missions() == ("mission-a", "mission-b")
'@

Write-Utf8NoBom "tests\test_mission_orchestration_executor.py" @'
from pathlib import Path

from forge.mission_orchestration.executor import MissionExecutor
from forge.mission_orchestration.models import (
    ApprovalDecision,
    MissionApproval,
    MissionStatus,
)
from forge.mission_orchestration.service import MissionOrchestrationService


def execution_for(tmp_path: Path):
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
'@

Write-Utf8NoBom "tests\test_mission_orchestration_service.py" @'
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
'@

Write-Host ""
Write-Host "M3.6 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_mission_orchestration_store.py `
    .\tests\test_mission_orchestration_executor.py `
    .\tests\test_mission_orchestration_service.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.6 PACKAGE 2 COMPLETE" -ForegroundColor Green
git status --short