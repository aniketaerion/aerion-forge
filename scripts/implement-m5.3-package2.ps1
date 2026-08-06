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

    New-Item `
        -ItemType Directory `
        -Path $Directory `
        -Force | Out-Null

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

$ExpectedBranch = "feature/m5.3-autonomous-mission-orchestrator"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.3 Package 2 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_orchestration\plan_loader.py" @'
"""Approved-plan loading and version validation."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_runtime.models import MissionPlan


@dataclass(slots=True)
class InMemoryApprovedPlanStore:
    """In-memory approved-plan store keyed by mission."""

    _plans: dict[str, MissionPlan] = field(default_factory=dict)

    def register(self, plan: MissionPlan) -> None:
        existing = self._plans.get(plan.mission_id)

        if existing is not None and existing.version >= plan.version:
            raise OrchestrationContractError(
                "Approved plan version must increase."
            )

        self._plans[plan.mission_id] = plan

    def load(
        self,
        mission_id: str,
        *,
        expected_plan_id: str,
        expected_version: int,
    ) -> MissionPlan:
        try:
            plan = self._plans[mission_id]
        except KeyError as exc:
            raise OrchestrationContractError(
                f"No approved plan exists for mission: {mission_id}"
            ) from exc

        if plan.plan_id != expected_plan_id:
            raise OrchestrationContractError(
                "Approved plan identifier mismatch."
            )

        if plan.version != expected_version:
            raise OrchestrationContractError(
                "Approved plan version mismatch."
            )

        return plan
'@

Write-Utf8NoBom "forge\autonomous_orchestration\progress.py" @'
"""Mission-session progress evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_runtime.models import MissionPlan


@dataclass(frozen=True, slots=True)
class MissionProgress:
    """Deterministic progress snapshot."""

    total_steps: int
    completed_steps: int
    failed_steps: int
    remaining_steps: int
    completion_percent: float
    complete: bool


def evaluate_progress(
    session: MissionSession,
    plan: MissionPlan,
) -> MissionProgress:
    """Evaluate mission completion from session and plan state."""
    plan_step_ids = {step.step_id for step in plan.steps}
    completed = plan_step_ids.intersection(session.completed_step_ids)
    failed = plan_step_ids.intersection(session.failed_step_ids)
    total = len(plan_step_ids)
    remaining = total - len(completed)

    percentage = (
        100.0
        if total == 0
        else round((len(completed) / total) * 100.0, 2)
    )

    return MissionProgress(
        total_steps=total,
        completed_steps=len(completed),
        failed_steps=len(failed),
        remaining_steps=remaining,
        completion_percent=percentage,
        complete=remaining == 0 and not failed,
    )
'@

Write-Utf8NoBom "forge\autonomous_orchestration\budget_monitor.py" @'
"""Bounded orchestration budget checks."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)


@dataclass(frozen=True, slots=True)
class BudgetEvaluation:
    """Result of orchestration-budget evaluation."""

    allowed: bool
    exhausted: tuple[str, ...]


def evaluate_budgets(
    session: MissionSession,
    policy: AutonomousOrchestrationPolicy,
) -> BudgetEvaluation:
    """Evaluate all bounded orchestration counters."""
    exhausted: list[str] = []
    budgets = policy.budgets

    if session.cycle_count >= budgets.maximum_cycles:
        exhausted.append("maximum_cycles")

    if session.execution_count >= budgets.maximum_step_executions:
        exhausted.append("maximum_step_executions")

    if session.retry_count >= budgets.maximum_retries:
        exhausted.append("maximum_retries")

    if session.rollback_count >= budgets.maximum_rollbacks:
        exhausted.append("maximum_rollbacks")

    if session.replan_count >= budgets.maximum_replans:
        exhausted.append("maximum_replans")

    return BudgetEvaluation(
        allowed=not exhausted,
        exhausted=tuple(exhausted),
    )
'@

Write-Utf8NoBom "forge\autonomous_orchestration\execution_factory.py" @'
"""Factories for one bounded M5.2 execution request."""

from __future__ import annotations

from forge.autonomous_execution.identifiers import (
    execution_request_identifier,
)
from forge.autonomous_execution.models import ExecutionRequest
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationRequest,
)
from forge.autonomous_runtime.models import MissionStep


def build_execution_request(
    orchestration_request: OrchestrationRequest,
    session: MissionSession,
    step: MissionStep,
) -> ExecutionRequest:
    """Create one deterministic execution request."""
    payload = {
        "mission_id": session.mission_id,
        "plan_id": session.plan_id,
        "step_id": step.step_id,
        "session_version": session.version,
        "cycle_count": session.cycle_count,
    }

    return ExecutionRequest(
        request_id=execution_request_identifier(payload),
        mission_id=session.mission_id,
        plan_id=session.plan_id,
        step_id=step.step_id,
        repository_root=session.repository_root,
        dry_run=orchestration_request.dry_run,
        requested_by=orchestration_request.requested_by,
    )
'@

Write-Utf8NoBom "forge\autonomous_orchestration\coordinator.py" @'
"""Coordinate one bounded autonomous mission iteration."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.planner import (
    AutonomousExecutionPlanner,
)
from forge.autonomous_orchestration.budget_monitor import (
    evaluate_budgets,
)
from forge.autonomous_orchestration.execution_factory import (
    build_execution_request,
)
from forge.autonomous_orchestration.identifiers import (
    orchestration_iteration_identifier,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationIteration,
    OrchestrationRequest,
    utc_now,
)
from forge.autonomous_orchestration.plan_loader import (
    InMemoryApprovedPlanStore,
)
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)
from forge.autonomous_orchestration.progress import evaluate_progress
from forge.autonomous_orchestration.states import IterationOutcome
from forge.autonomous_runtime.models import AutonomousMission


@dataclass(frozen=True, slots=True)
class CoordinationResult:
    """Result of one orchestration coordination cycle."""

    session: MissionSession
    iteration: OrchestrationIteration
    execution_request_id: str | None
    selected_step_id: str | None


@dataclass(slots=True)
class MissionStepCoordinator:
    """Select one next step and prepare one M5.2 execution request."""

    plan_store: InMemoryApprovedPlanStore
    planner: AutonomousExecutionPlanner
    policy: AutonomousOrchestrationPolicy

    def coordinate(
        self,
        request: OrchestrationRequest,
        session: MissionSession,
        mission: AutonomousMission,
    ) -> CoordinationResult:
        plan = self.plan_store.load(
            session.mission_id,
            expected_plan_id=session.plan_id,
            expected_version=session.plan_version,
        )

        budget = evaluate_budgets(session, self.policy)
        if not budget.allowed:
            iteration = self._iteration(
                session=session,
                outcome=IterationOutcome.ESCALATED,
                selected_step_id=None,
                execution_request_id=None,
            )
            return CoordinationResult(
                session=session,
                iteration=iteration,
                execution_request_id=None,
                selected_step_id=None,
            )

        progress = evaluate_progress(session, plan)
        if progress.complete:
            iteration = self._iteration(
                session=session,
                outcome=IterationOutcome.MISSION_COMPLETED,
                selected_step_id=None,
                execution_request_id=None,
            )
            return CoordinationResult(
                session=session,
                iteration=iteration,
                execution_request_id=None,
                selected_step_id=None,
            )

        selection = self.planner.select_next(
            mission,
            plan,
            completed_step_ids=frozenset(
                session.completed_step_ids
            ),
        )

        if selection.step is None:
            iteration = self._iteration(
                session=session,
                outcome=IterationOutcome.NO_ELIGIBLE_STEP,
                selected_step_id=None,
                execution_request_id=None,
            )
            return CoordinationResult(
                session=session,
                iteration=iteration,
                execution_request_id=None,
                selected_step_id=None,
            )

        execution_request = build_execution_request(
            request,
            session,
            selection.step,
        )
        updated_session = session.model_copy(
            update={
                "current_step_id": selection.step.step_id,
                "cycle_count": session.cycle_count + 1,
                "version": session.version + 1,
                "updated_at": utc_now(),
            }
        )
        iteration = self._iteration(
            session=updated_session,
            outcome=IterationOutcome.STEP_SELECTED,
            selected_step_id=selection.step.step_id,
            execution_request_id=execution_request.request_id,
        )

        return CoordinationResult(
            session=updated_session,
            iteration=iteration,
            execution_request_id=execution_request.request_id,
            selected_step_id=selection.step.step_id,
        )

    @staticmethod
    def _iteration(
        *,
        session: MissionSession,
        outcome: IterationOutcome,
        selected_step_id: str | None,
        execution_request_id: str | None,
    ) -> OrchestrationIteration:
        sequence = session.cycle_count + 1
        payload = {
            "session_id": session.session_id,
            "sequence": sequence,
            "selected_step_id": selected_step_id,
            "execution_request_id": execution_request_id,
            "outcome": outcome.value,
        }

        return OrchestrationIteration(
            iteration_id=orchestration_iteration_identifier(payload),
            session_id=session.session_id,
            sequence=sequence,
            mission_version_before=session.version,
            selected_step_id=selected_step_id,
            execution_request_id=execution_request_id,
            outcome=outcome,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_plan_loader.py" @'
import pytest

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_orchestration.plan_loader import (
    InMemoryApprovedPlanStore,
)
from forge.autonomous_runtime.models import MissionPlan


def plan(version: int = 1) -> MissionPlan:
    return MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        version=version,
        objective_summary="Execute mission.",
        completion_criteria=("Mission complete.",),
        steps=(),
    )


def test_plan_store_loads_expected_version() -> None:
    store = InMemoryApprovedPlanStore()
    store.register(plan())

    loaded = store.load(
        "mission-1",
        expected_plan_id="plan-1",
        expected_version=1,
    )

    assert loaded.version == 1


def test_plan_version_mismatch_is_rejected() -> None:
    store = InMemoryApprovedPlanStore()
    store.register(plan())

    with pytest.raises(OrchestrationContractError):
        store.load(
            "mission-1",
            expected_plan_id="plan-1",
            expected_version=2,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_progress.py" @'
from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.progress import evaluate_progress
from forge.autonomous_runtime.models import MissionPlan, MissionStep


def step(step_id: str, sequence: int) -> MissionStep:
    return MissionStep(
        step_id=step_id,
        plan_id="plan-1",
        sequence=sequence,
        title=step_id,
        description=f"Execute {step_id}.",
        action_kind="read_file",
    )


def test_progress_calculates_completion() -> None:
    plan = MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        objective_summary="Execute mission.",
        completion_criteria=("Mission complete.",),
        steps=(step("step-1", 1), step("step-2", 2)),
    )
    session = MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        completed_step_ids=("step-1",),
    )

    progress = evaluate_progress(session, plan)

    assert progress.completed_steps == 1
    assert progress.remaining_steps == 1
    assert progress.completion_percent == 50.0
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_budget_monitor.py" @'
from forge.autonomous_orchestration.budget_monitor import (
    evaluate_budgets,
)
from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)


def test_budget_monitor_detects_cycle_exhaustion() -> None:
    policy = AutonomousOrchestrationPolicy()
    session = MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        cycle_count=policy.budgets.maximum_cycles,
    )

    result = evaluate_budgets(session, policy)

    assert not result.allowed
    assert "maximum_cycles" in result.exhausted
'@

Write-Utf8NoBom "tests\test_autonomous_orchestration_coordinator.py" @'
from forge.autonomous_execution.planner import (
    AutonomousExecutionPlanner,
)
from forge.autonomous_orchestration.coordinator import (
    MissionStepCoordinator,
)
from forge.autonomous_orchestration.models import (
    MissionSession,
    OrchestrationRequest,
)
from forge.autonomous_orchestration.plan_loader import (
    InMemoryApprovedPlanStore,
)
from forge.autonomous_orchestration.policies import (
    AutonomousOrchestrationPolicy,
)
from forge.autonomous_orchestration.states import IterationOutcome
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionPlan,
    MissionRequest,
    MissionStep,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Execute mission.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        state=MissionState.EXECUTING,
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def test_coordinator_selects_one_step() -> None:
    plan = MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        objective_summary="Execute mission.",
        completion_criteria=("Mission complete.",),
        steps=(
            MissionStep(
                step_id="step-1",
                plan_id="plan-1",
                sequence=1,
                title="Inspect repository",
                description="Inspect repository.",
                action_kind="read_file",
            ),
        ),
    )
    store = InMemoryApprovedPlanStore()
    store.register(plan)

    coordinator = MissionStepCoordinator(
        plan_store=store,
        planner=AutonomousExecutionPlanner(),
        policy=AutonomousOrchestrationPolicy(),
    )
    session = MissionSession(
        session_id="session-1",
        mission_id="mission-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
    )

    result = coordinator.coordinate(
        OrchestrationRequest(
            request_id="orchestration-request-1",
            mission_id="mission-1",
            repository_root="repository",
            requested_by="Aerion",
        ),
        session,
        mission(),
    )

    assert result.selected_step_id == "step-1"
    assert result.execution_request_id is not None
    assert result.iteration.outcome is IterationOutcome.STEP_SELECTED
    assert result.session.current_step_id == "step-1"
'@

Write-Host ""
Write-Host "M5.3 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_orchestration_plan_loader.py `
    .\tests\test_autonomous_orchestration_progress.py `
    .\tests\test_autonomous_orchestration_budget_monitor.py `
    .\tests\test_autonomous_orchestration_coordinator.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.3 Package 2 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.3 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short