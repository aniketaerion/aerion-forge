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

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Write-Utf8NoBom "forge\agent_runtime\state.py" @'
"""Lifecycle state machine for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from datetime import UTC, datetime

from forge.agent_runtime.errors import AgentRuntimeStateError
from forge.agent_runtime.models import (
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    AgentStageStatus,
)

_ALLOWED_TRANSITIONS: dict[
    AgentSessionStatus,
    frozenset[AgentSessionStatus],
] = {
    AgentSessionStatus.CREATED: frozenset(
        {
            AgentSessionStatus.PLANNING,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.PLANNING: frozenset(
        {
            AgentSessionStatus.AWAITING_APPROVAL,
            AgentSessionStatus.EXECUTING,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.AWAITING_APPROVAL: frozenset(
        {
            AgentSessionStatus.EXECUTING,
            AgentSessionStatus.REPAIRING,
            AgentSessionStatus.VERIFYING,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
            AgentSessionStatus.FAILED,
        }
    ),
    AgentSessionStatus.EXECUTING: frozenset(
        {
            AgentSessionStatus.VALIDATING,
            AgentSessionStatus.AWAITING_APPROVAL,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.VALIDATING: frozenset(
        {
            AgentSessionStatus.REPAIRING,
            AgentSessionStatus.VERIFYING,
            AgentSessionStatus.COMPLETED,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.REPAIRING: frozenset(
        {
            AgentSessionStatus.VALIDATING,
            AgentSessionStatus.AWAITING_APPROVAL,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.VERIFYING: frozenset(
        {
            AgentSessionStatus.AWAITING_APPROVAL,
            AgentSessionStatus.COMPLETED,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.PAUSED,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.PAUSED: frozenset(
        {
            AgentSessionStatus.PLANNING,
            AgentSessionStatus.AWAITING_APPROVAL,
            AgentSessionStatus.EXECUTING,
            AgentSessionStatus.VALIDATING,
            AgentSessionStatus.REPAIRING,
            AgentSessionStatus.VERIFYING,
            AgentSessionStatus.CANCELLED,
        }
    ),
    AgentSessionStatus.COMPLETED: frozenset(),
    AgentSessionStatus.FAILED: frozenset(),
    AgentSessionStatus.CANCELLED: frozenset(),
}


def can_transition(
    current: AgentSessionStatus,
    target: AgentSessionStatus,
) -> bool:
    """Return whether the session lifecycle transition is permitted."""
    return target in _ALLOWED_TRANSITIONS[current]


def transition_session(
    session: AgentSession,
    target: AgentSessionStatus,
    *,
    current_stage_id: str | None = None,
) -> AgentSession:
    """Transition a session while preserving immutable history."""
    if target is session.status:
        return session

    if not can_transition(session.status, target):
        raise AgentRuntimeStateError(
            "invalid agent-session transition: "
            f"{session.status.value} -> {target.value}"
        )

    return session.model_copy(
        update={
            "status": target,
            "current_stage_id": current_stage_id,
            "updated_at": datetime.now(UTC),
        }
    )


def completed_stage_ids(
    session: AgentSession,
) -> frozenset[str]:
    """Return successfully completed runtime stage identifiers."""
    return frozenset(
        result.stage_id
        for result in session.stage_results
        if result.status is AgentStageStatus.SUCCEEDED
    )


def failed_required_stage(
    session: AgentSession,
) -> AgentStage | None:
    """Return the first required stage that failed or was blocked."""
    stages = {stage.stage_id: stage for stage in session.stages}

    for result in session.stage_results:
        if result.status not in {
            AgentStageStatus.FAILED,
            AgentStageStatus.BLOCKED,
        }:
            continue

        stage = stages[result.stage_id]
        if stage.required:
            return stage

    return None


def next_ready_stage(
    session: AgentSession,
) -> AgentStage | None:
    """Return the next dependency-satisfied, unexecuted stage."""
    completed = completed_stage_ids(session)
    executed = {
        result.stage_id
        for result in session.stage_results
    }

    for stage in sorted(
        session.stages,
        key=lambda item: item.sequence,
    ):
        if stage.stage_id in executed:
            continue

        if set(stage.depends_on).issubset(completed):
            return stage

    return None


def append_stage_result(
    session: AgentSession,
    result: AgentStageResult,
) -> AgentSession:
    """Append exactly one stage result to immutable session state."""
    known_stage_ids = {
        stage.stage_id for stage in session.stages
    }

    if result.stage_id not in known_stage_ids:
        raise AgentRuntimeStateError(
            f"stage result references unknown stage: {result.stage_id}"
        )

    if any(
        existing.stage_id == result.stage_id
        for existing in session.stage_results
    ):
        raise AgentRuntimeStateError(
            f"stage already has a result: {result.stage_id}"
        )

    return session.model_copy(
        update={
            "stage_results": (
                *session.stage_results,
                result,
            ),
            "current_stage_id": result.stage_id,
            "updated_at": datetime.now(UTC),
        }
    )
'@

Write-Utf8NoBom "forge\agent_runtime\executor.py" @'
"""Execution engine for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.errors import (
    AgentRuntimeApprovalError,
    AgentRuntimeExecutionError,
)
from forge.agent_runtime.models import (
    AgentRuntimePolicy,
    AgentSession,
    AgentSessionStatus,
    AgentStageStatus,
    ApprovalKind,
)
from forge.agent_runtime.policies import require_approval
from forge.agent_runtime.registry import AgentCapabilityRegistry
from forge.agent_runtime.state import (
    append_stage_result,
    failed_required_stage,
    next_ready_stage,
    transition_session,
)


def _status_for_stage(
    stage_capability: str,
) -> AgentSessionStatus:
    if stage_capability == "mission_planning":
        return AgentSessionStatus.PLANNING
    if stage_capability in {
        "validation_repair",
        "build_verification",
    }:
        return AgentSessionStatus.VERIFYING
    if stage_capability == "autonomous_repair":
        return AgentSessionStatus.REPAIRING
    return AgentSessionStatus.EXECUTING


class AgentRuntimeExecutor:
    """Execute one stage at a time through registered adapters."""

    def __init__(
        self,
        registry: AgentCapabilityRegistry,
        policy: AgentRuntimePolicy | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or AgentRuntimePolicy()

    def run_next(
        self,
        session: AgentSession,
        *,
        repository_root: Path,
        context: Mapping[str, Any] | None = None,
    ) -> AgentSession:
        """Execute exactly one ready stage or finalize the session."""
        if session.status in {
            AgentSessionStatus.COMPLETED,
            AgentSessionStatus.FAILED,
            AgentSessionStatus.CANCELLED,
        }:
            raise AgentRuntimeExecutionError(
                f"cannot execute terminal session: {session.status.value}"
            )

        failed = failed_required_stage(session)
        if failed is not None:
            if session.status is AgentSessionStatus.FAILED:
                return session
            return transition_session(
                session,
                AgentSessionStatus.FAILED,
                current_stage_id=failed.stage_id,
            )

        stage = next_ready_stage(session)
        if stage is None:
            if len(session.stage_results) == len(session.stages):
                if session.status is AgentSessionStatus.COMPLETED:
                    return session
                return transition_session(
                    session,
                    AgentSessionStatus.COMPLETED,
                    current_stage_id=None,
                )

            raise AgentRuntimeExecutionError(
                "no dependency-satisfied stage is available"
            )

        if stage.requires_approval is not None:
            try:
                require_approval(
                    session.approvals,
                    stage.requires_approval,
                    self.policy,
                )
            except AgentRuntimeApprovalError:
                if session.status is AgentSessionStatus.AWAITING_APPROVAL:
                    return session

                return transition_session(
                    session,
                    AgentSessionStatus.AWAITING_APPROVAL,
                    current_stage_id=stage.stage_id,
                )

        target_status = _status_for_stage(stage.capability.value)
        active = (
            session
            if session.status is target_status
            else transition_session(
                session,
                target_status,
                current_stage_id=stage.stage_id,
            )
        )

        adapter = self.registry.get(stage.capability)

        try:
            result = adapter.execute(
                repository_root.resolve(),
                active,
                stage,
                context or {},
            )
        except Exception as exc:
            raise AgentRuntimeExecutionError(
                f"stage execution failed: {stage.stage_id}"
            ) from exc

        updated = append_stage_result(active, result)

        if (
            stage.required
            and result.status
            in {
                AgentStageStatus.FAILED,
                AgentStageStatus.BLOCKED,
            }
        ):
            return transition_session(
                updated,
                AgentSessionStatus.FAILED,
                current_stage_id=stage.stage_id,
            )

        return updated

    def run_to_boundary(
        self,
        session: AgentSession,
        *,
        repository_root: Path,
        context: Mapping[str, Any] | None = None,
    ) -> AgentSession:
        """Execute until approval, failure, cancellation, or completion."""
        current = session

        for _ in range(current.request.max_stages + 1):
            before = current
            current = self.run_next(
                current,
                repository_root=repository_root,
                context=context,
            )

            if current.status in {
                AgentSessionStatus.AWAITING_APPROVAL,
                AgentSessionStatus.COMPLETED,
                AgentSessionStatus.FAILED,
                AgentSessionStatus.CANCELLED,
            }:
                return current

            if current == before:
                raise AgentRuntimeExecutionError(
                    "agent runtime made no execution progress"
                )

        raise AgentRuntimeExecutionError(
            "agent runtime exceeded request stage bound"
        )


def required_approval_for_status(
    status: AgentSessionStatus,
) -> ApprovalKind | None:
    """Map runtime boundaries to their expected approval kind."""
    if status is AgentSessionStatus.PLANNING:
        return ApprovalKind.PLAN
    if status is AgentSessionStatus.EXECUTING:
        return ApprovalKind.EDIT
    if status is AgentSessionStatus.REPAIRING:
        return ApprovalKind.REPAIR
    if status is AgentSessionStatus.VERIFYING:
        return ApprovalKind.RELEASE
    return None
'@

Write-Utf8NoBom "forge\agent_runtime\service.py" @'
"""Application service for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from forge.agent_runtime.executor import AgentRuntimeExecutor
from forge.agent_runtime.identifiers import (
    agent_request_identifier,
    agent_session_identifier,
    agent_stage_identifier,
)
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentRuntimePolicy,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    ApprovalKind,
)
from forge.agent_runtime.policies import (
    resolve_repository_root,
    validate_request,
    validate_self_modification,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry


_DEFAULT_PIPELINE: tuple[
    tuple[AgentCapability, str, ApprovalKind | None],
    ...,
] = (
    (
        AgentCapability.MISSION_PLANNING,
        "Mission Planning",
        ApprovalKind.PLAN,
    ),
    (
        AgentCapability.IMPACT_ANALYSIS,
        "Impact Analysis",
        None,
    ),
    (
        AgentCapability.SAFE_CHANGE_PLANNING,
        "Safe Change Planning",
        ApprovalKind.EDIT,
    ),
    (
        AgentCapability.SAFE_CODE_EDITING,
        "Safe Code Editing",
        ApprovalKind.EDIT,
    ),
    (
        AgentCapability.AUTONOMOUS_REPAIR,
        "Autonomous Repair",
        ApprovalKind.REPAIR,
    ),
    (
        AgentCapability.BUILD_VERIFICATION,
        "Build Verification",
        ApprovalKind.RELEASE,
    ),
)


class AgentRuntimeService:
    """Create and operate unified engineering-agent sessions."""

    def __init__(
        self,
        registry: AgentCapabilityRegistry,
        policy: AgentRuntimePolicy | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or AgentRuntimePolicy()
        self.executor = AgentRuntimeExecutor(
            registry,
            self.policy,
        )

    def create_request(
        self,
        objective: AgentObjective,
        *,
        dry_run: bool = True,
        allow_code_changes: bool = False,
        max_stages: int | None = None,
        max_repair_attempts: int | None = None,
    ) -> AgentRuntimeRequest:
        """Create and validate one deterministic runtime request."""
        root = resolve_repository_root(
            objective.repository_root
        )
        validate_self_modification(
            root,
            objective.target_paths,
            self.policy,
        )

        payload = {
            "objective": objective.objective,
            "repository_root": str(root),
            "target_paths": objective.target_paths,
            "constraints": objective.constraints,
            "acceptance_criteria": objective.acceptance_criteria,
            "requested_capabilities": [
                capability.value
                for capability
                in objective.requested_capabilities
            ],
            "dry_run": dry_run,
            "allow_code_changes": allow_code_changes,
        }

        request = AgentRuntimeRequest(
            request_id=agent_request_identifier(payload),
            objective=objective.model_copy(
                update={"repository_root": str(root)}
            ),
            dry_run=dry_run,
            allow_code_changes=allow_code_changes,
            max_stages=(
                max_stages
                if max_stages is not None
                else self.policy.max_stages
            ),
            max_repair_attempts=(
                max_repair_attempts
                if max_repair_attempts is not None
                else self.policy.max_repair_attempts
            ),
        )
        validate_request(request, self.policy)
        return request

    def create_session(
        self,
        request: AgentRuntimeRequest,
    ) -> AgentSession:
        """Create a deterministic runtime session and stage graph."""
        requested = (
            request.objective.requested_capabilities
            or tuple(
                capability
                for capability, _, _
                in _DEFAULT_PIPELINE
            )
        )

        definitions = tuple(
            definition
            for definition in _DEFAULT_PIPELINE
            if definition[0] in requested
        )

        self.registry.validate_required(
            capability
            for capability, _, _
            in definitions
        )

        stages: list[AgentStage] = []
        previous_stage_id: str | None = None

        for sequence, (
            capability,
            name,
            approval,
        ) in enumerate(definitions, start=1):
            stage_id = agent_stage_identifier(
                {
                    "request_id": request.request_id,
                    "sequence": sequence,
                    "capability": capability.value,
                }
            )
            stages.append(
                AgentStage(
                    stage_id=stage_id,
                    sequence=sequence,
                    capability=capability,
                    name=name,
                    requires_approval=approval,
                    depends_on=(
                        (previous_stage_id,)
                        if previous_stage_id is not None
                        else ()
                    ),
                )
            )
            previous_stage_id = stage_id

        session_id = agent_session_identifier(
            {
                "request_id": request.request_id,
                "stage_ids": [
                    stage.stage_id for stage in stages
                ],
            }
        )

        return AgentSession(
            session_id=session_id,
            request=request,
            status=AgentSessionStatus.CREATED,
            stages=tuple(stages),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def add_approval(
        self,
        session: AgentSession,
        approval: AgentApproval,
    ) -> AgentSession:
        """Append one immutable human approval to a session."""
        if any(
            existing.approval_id == approval.approval_id
            for existing in session.approvals
        ):
            return session

        return session.model_copy(
            update={
                "approvals": (
                    *session.approvals,
                    approval,
                ),
                "updated_at": datetime.now(UTC),
            }
        )

    def run_next(
        self,
        session: AgentSession,
        *,
        context: dict[str, object] | None = None,
    ) -> AgentSession:
        """Execute exactly one runtime stage."""
        return self.executor.run_next(
            session,
            repository_root=Path(
                session.request.objective.repository_root
            ),
            context=context or {},
        )

    def run_to_boundary(
        self,
        session: AgentSession,
        *,
        context: dict[str, object] | None = None,
    ) -> AgentSession:
        """Execute until approval, failure, or completion."""
        return self.executor.run_to_boundary(
            session,
            repository_root=Path(
                session.request.objective.repository_root
            ),
            context=context or {},
        )
'@

Write-Utf8NoBom "tests\test_agent_runtime_state.py" @'
from datetime import UTC, datetime

import pytest

from forge.agent_runtime.errors import AgentRuntimeStateError
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    AgentStageStatus,
)
from forge.agent_runtime.state import (
    append_stage_result,
    can_transition,
    next_ready_stage,
    transition_session,
)


def session_for() -> AgentSession:
    first = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan",
    )
    second = AgentStage(
        stage_id="stage-2",
        sequence=2,
        capability=AgentCapability.IMPACT_ANALYSIS,
        name="Impact",
        depends_on=("stage-1",),
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )
    return AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.CREATED,
        stages=(first, second),
    )


def test_valid_transition_is_allowed() -> None:
    assert can_transition(
        AgentSessionStatus.CREATED,
        AgentSessionStatus.PLANNING,
    )


def test_invalid_transition_is_rejected() -> None:
    with pytest.raises(AgentRuntimeStateError):
        transition_session(
            session_for(),
            AgentSessionStatus.COMPLETED,
        )


def test_next_ready_stage_respects_dependencies() -> None:
    session = session_for()

    assert next_ready_stage(session).stage_id == "stage-1"

    completed = AgentStageResult(
        stage_id="stage-1",
        status=AgentStageStatus.SUCCEEDED,
        summary="done",
        completed_at=datetime.now(UTC),
    )
    updated = append_stage_result(session, completed)

    assert next_ready_stage(updated).stage_id == "stage-2"


def test_duplicate_stage_result_is_rejected() -> None:
    session = session_for()
    result = AgentStageResult(
        stage_id="stage-1",
        status=AgentStageStatus.SUCCEEDED,
        summary="done",
        completed_at=datetime.now(UTC),
    )
    updated = append_stage_result(session, result)

    with pytest.raises(AgentRuntimeStateError):
        append_stage_result(updated, result)
'@

Write-Utf8NoBom "tests\test_agent_runtime_executor.py" @'
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import (
    AgentCapabilityAdapter,
    succeeded_result,
)
from forge.agent_runtime.executor import AgentRuntimeExecutor
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentRuntimePolicy,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    ApprovalKind,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry


class SuccessAdapter(AgentCapabilityAdapter):
    capability = AgentCapability.MISSION_PLANNING

    def execute(
        self,
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return succeeded_result(stage, "planned")


def session_for(*, approved: bool) -> AgentSession:
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan",
        requires_approval=ApprovalKind.PLAN,
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )
    approvals = (
        (
            AgentApproval(
                approval_id="approval-1",
                kind=ApprovalKind.PLAN,
                approved=True,
                approved_by="operator",
                reason="approved",
            ),
        )
        if approved
        else ()
    )
    return AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.CREATED,
        stages=(stage,),
        approvals=approvals,
    )


def test_executor_stops_at_missing_approval(
    tmp_path: Path,
) -> None:
    registry = AgentCapabilityRegistry((SuccessAdapter(),))
    executor = AgentRuntimeExecutor(
        registry,
        AgentRuntimePolicy(),
    )

    updated = executor.run_next(
        session_for(approved=False),
        repository_root=tmp_path,
    )

    assert updated.status is AgentSessionStatus.AWAITING_APPROVAL
    assert not updated.stage_results


def test_executor_runs_approved_stage(tmp_path: Path) -> None:
    registry = AgentCapabilityRegistry((SuccessAdapter(),))
    executor = AgentRuntimeExecutor(
        registry,
        AgentRuntimePolicy(),
    )

    updated = executor.run_next(
        session_for(approved=True),
        repository_root=tmp_path,
    )

    assert len(updated.stage_results) == 1
    assert updated.stage_results[0].summary == "planned"
'@

Write-Utf8NoBom "tests\test_agent_runtime_service.py" @'
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import (
    AgentCapabilityAdapter,
    succeeded_result,
)
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentRuntimePolicy,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
    ApprovalKind,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry
from forge.agent_runtime.service import AgentRuntimeService


class PlanningAdapter(AgentCapabilityAdapter):
    capability = AgentCapability.MISSION_PLANNING

    def execute(
        self,
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        del repository_root, session, context
        return succeeded_result(stage, "planned")


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_service_creates_deterministic_session(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    registry = AgentCapabilityRegistry((PlanningAdapter(),))
    policy = AgentRuntimePolicy(
        allowed_capabilities=(
            AgentCapability.MISSION_PLANNING,
        )
    )
    service = AgentRuntimeService(registry, policy)
    objective = AgentObjective(
        objective="Plan feature",
        repository_root=str(tmp_path),
        requested_capabilities=(
            AgentCapability.MISSION_PLANNING,
        ),
    )

    request = service.create_request(objective)
    first = service.create_session(request)
    second = service.create_session(request)

    assert first.session_id == second.session_id
    assert first.stages == second.stages


def test_service_runs_session_to_completion(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    registry = AgentCapabilityRegistry((PlanningAdapter(),))
    policy = AgentRuntimePolicy(
        allowed_capabilities=(
            AgentCapability.MISSION_PLANNING,
        )
    )
    service = AgentRuntimeService(registry, policy)
    objective = AgentObjective(
        objective="Plan feature",
        repository_root=str(tmp_path),
        requested_capabilities=(
            AgentCapability.MISSION_PLANNING,
        ),
    )
    request = service.create_request(objective)
    session = service.create_session(request)
    approval = AgentApproval(
        approval_id="approval-1",
        kind=ApprovalKind.PLAN,
        approved=True,
        approved_by="operator",
        reason="approved",
    )
    approved = service.add_approval(session, approval)

    executed = service.run_to_boundary(approved)
    completed = service.run_to_boundary(executed)

    assert completed.status is AgentSessionStatus.COMPLETED
    assert len(completed.stage_results) == 1
'@

Write-Host ""
Write-Host "M3.8 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_agent_runtime_state.py `
    .\tests\test_agent_runtime_executor.py `
    .\tests\test_agent_runtime_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M3.8 Package 2 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M3.8 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short
