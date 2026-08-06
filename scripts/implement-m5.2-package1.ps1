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

$ExpectedBranch = "feature/m5.2-autonomous-execution-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.2 Package 1 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_execution\dependency_graph.py" @'
"""Dependency graph evaluation for executable mission steps."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_runtime.models import MissionStep


@dataclass(frozen=True, slots=True)
class DependencyEvaluation:
    """Dependency evaluation for one step."""

    satisfied: bool
    missing_dependencies: tuple[str, ...]


def evaluate_dependencies(
    step: MissionStep,
    *,
    completed_step_ids: frozenset[str],
) -> DependencyEvaluation:
    """Check whether all dependencies for a step are complete."""
    missing = tuple(
        dependency
        for dependency in step.depends_on
        if dependency not in completed_step_ids
    )
    return DependencyEvaluation(
        satisfied=not missing,
        missing_dependencies=missing,
    )


def assert_dependencies_satisfied(
    step: MissionStep,
    *,
    completed_step_ids: frozenset[str],
) -> None:
    """Raise when step dependencies are incomplete."""
    result = evaluate_dependencies(
        step,
        completed_step_ids=completed_step_ids,
    )
    if not result.satisfied:
        raise ExecutionContractError(
            "Step dependencies are incomplete: "
            + ", ".join(result.missing_dependencies)
        )


def validate_dependency_graph(
    steps: tuple[MissionStep, ...],
) -> None:
    """Reject unknown dependencies, self-dependencies, and cycles."""
    step_ids = {step.step_id for step in steps}

    for step in steps:
        unknown = set(step.depends_on).difference(step_ids)
        if unknown:
            raise ExecutionContractError(
                f"Step {step.step_id} has unknown dependencies: "
                + ", ".join(sorted(unknown))
            )
        if step.step_id in step.depends_on:
            raise ExecutionContractError(
                f"Step {step.step_id} cannot depend on itself."
            )

    dependencies = {
        step.step_id: set(step.depends_on)
        for step in steps
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(step_id: str) -> None:
        if step_id in visited:
            return
        if step_id in visiting:
            raise ExecutionContractError(
                "Execution plan contains a dependency cycle."
            )

        visiting.add(step_id)
        for dependency in dependencies[step_id]:
            visit(dependency)
        visiting.remove(step_id)
        visited.add(step_id)

    for step_id in sorted(step_ids):
        visit(step_id)
'@

Write-Utf8NoBom "forge\autonomous_execution\eligibility.py" @'
"""Step eligibility evaluation for autonomous execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.dependency_graph import (
    evaluate_dependencies,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionStep,
)
from forge.autonomous_runtime.states import (
    MissionState,
    StepStatus,
)


@dataclass(frozen=True, slots=True)
class EligibilityEvaluation:
    """Deterministic step eligibility result."""

    eligible: bool
    reasons: tuple[str, ...]


def evaluate_step_eligibility(
    mission: AutonomousMission,
    step: MissionStep,
    *,
    completed_step_ids: frozenset[str],
) -> EligibilityEvaluation:
    """Evaluate whether a step can enter execution."""
    reasons: list[str] = []

    if mission.state is not MissionState.EXECUTING:
        reasons.append("Mission is not in executing state.")

    if step.status not in {
        StepStatus.PENDING,
        StepStatus.READY,
    }:
        reasons.append(
            f"Step status is not executable: {step.status.value}."
        )

    dependencies = evaluate_dependencies(
        step,
        completed_step_ids=completed_step_ids,
    )
    if not dependencies.satisfied:
        reasons.append(
            "Dependencies incomplete: "
            + ", ".join(dependencies.missing_dependencies)
        )

    if (
        step.required_authority
        > mission.granted_authority
    ):
        reasons.append(
            "Step authority exceeds mission grant."
        )

    return EligibilityEvaluation(
        eligible=not reasons,
        reasons=tuple(reasons),
    )
'@

Write-Utf8NoBom "forge\autonomous_execution\scheduler.py" @'
"""Deterministic scheduler for mission execution steps."""

from __future__ import annotations

from forge.autonomous_execution.dependency_graph import (
    validate_dependency_graph,
)
from forge.autonomous_execution.eligibility import (
    evaluate_step_eligibility,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionPlan,
    MissionStep,
)


def ordered_steps(
    plan: MissionPlan,
) -> tuple[MissionStep, ...]:
    """Return plan steps in deterministic sequence order."""
    validate_dependency_graph(plan.steps)
    return tuple(
        sorted(
            plan.steps,
            key=lambda step: (
                step.sequence,
                step.step_id,
            ),
        )
    )


def next_eligible_step(
    mission: AutonomousMission,
    plan: MissionPlan,
    *,
    completed_step_ids: frozenset[str],
) -> MissionStep | None:
    """Select the first eligible step deterministically."""
    for step in ordered_steps(plan):
        if step.step_id in completed_step_ids:
            continue

        result = evaluate_step_eligibility(
            mission,
            step,
            completed_step_ids=completed_step_ids,
        )
        if result.eligible:
            return step

    return None
'@

Write-Utf8NoBom "forge\autonomous_execution\execution_plan.py" @'
"""Executable plan projection for M5.2."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.dependency_graph import (
    validate_dependency_graph,
)
from forge.autonomous_execution.scheduler import ordered_steps
from forge.autonomous_runtime.models import MissionPlan, MissionStep


@dataclass(frozen=True, slots=True)
class ExecutablePlan:
    """Validated deterministic projection of a mission plan."""

    plan_id: str
    mission_id: str
    version: int
    steps: tuple[MissionStep, ...]
    total_steps: int


def build_executable_plan(
    plan: MissionPlan,
) -> ExecutablePlan:
    """Validate and project a mission plan for execution."""
    validate_dependency_graph(plan.steps)
    steps = ordered_steps(plan)

    return ExecutablePlan(
        plan_id=plan.plan_id,
        mission_id=plan.mission_id,
        version=plan.version,
        steps=steps,
        total_steps=len(steps),
    )
'@

Write-Utf8NoBom "forge\autonomous_execution\planner.py" @'
"""Application service for autonomous execution planning."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution.eligibility import (
    EligibilityEvaluation,
    evaluate_step_eligibility,
)
from forge.autonomous_execution.execution_plan import (
    ExecutablePlan,
    build_executable_plan,
)
from forge.autonomous_execution.scheduler import next_eligible_step
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionPlan,
    MissionStep,
)


@dataclass(frozen=True, slots=True)
class StepSelection:
    """Result of deterministic step selection."""

    step: MissionStep | None
    reason: str


class AutonomousExecutionPlanner:
    """Validate plans and select the next executable step."""

    def build(
        self,
        plan: MissionPlan,
    ) -> ExecutablePlan:
        return build_executable_plan(plan)

    def evaluate(
        self,
        mission: AutonomousMission,
        step: MissionStep,
        *,
        completed_step_ids: frozenset[str],
    ) -> EligibilityEvaluation:
        return evaluate_step_eligibility(
            mission,
            step,
            completed_step_ids=completed_step_ids,
        )

    def select_next(
        self,
        mission: AutonomousMission,
        plan: MissionPlan,
        *,
        completed_step_ids: frozenset[str],
    ) -> StepSelection:
        step = next_eligible_step(
            mission,
            plan,
            completed_step_ids=completed_step_ids,
        )

        if step is None:
            return StepSelection(
                step=None,
                reason="No eligible execution step is available.",
            )

        return StepSelection(
            step=step,
            reason="Selected first eligible step by sequence.",
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_dependency_graph.py" @'
import pytest

from forge.autonomous_execution.dependency_graph import (
    evaluate_dependencies,
    validate_dependency_graph,
)
from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_runtime.models import MissionStep


def step(
    step_id: str,
    sequence: int,
    depends_on: tuple[str, ...] = (),
) -> MissionStep:
    return MissionStep(
        step_id=step_id,
        plan_id="plan-1",
        sequence=sequence,
        title=step_id,
        description=f"Execute {step_id}.",
        action_kind="read_file",
        depends_on=depends_on,
    )


def test_dependency_evaluation_detects_missing_steps() -> None:
    result = evaluate_dependencies(
        step("step-2", 2, ("step-1",)),
        completed_step_ids=frozenset(),
    )

    assert not result.satisfied
    assert result.missing_dependencies == ("step-1",)


def test_dependency_cycle_is_rejected() -> None:
    with pytest.raises(ExecutionContractError):
        validate_dependency_graph(
            (
                step("step-1", 1, ("step-2",)),
                step("step-2", 2, ("step-1",)),
            )
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_eligibility.py" @'
from forge.autonomous_execution.eligibility import (
    evaluate_step_eligibility,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
    MissionStep,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)


def mission(
    state: MissionState = MissionState.EXECUTING,
) -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Execute approved steps.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        state=state,
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def step() -> MissionStep:
    return MissionStep(
        step_id="step-1",
        plan_id="plan-1",
        sequence=1,
        title="Inspect repository",
        description="Inspect repository safely.",
        action_kind="read_file",
    )


def test_step_is_eligible_for_executing_mission() -> None:
    result = evaluate_step_eligibility(
        mission(),
        step(),
        completed_step_ids=frozenset(),
    )

    assert result.eligible


def test_step_is_not_eligible_outside_execution_state() -> None:
    result = evaluate_step_eligibility(
        mission(MissionState.PLANNING),
        step(),
        completed_step_ids=frozenset(),
    )

    assert not result.eligible
    assert "Mission is not in executing state." in result.reasons
'@

Write-Utf8NoBom "tests\test_autonomous_execution_scheduler.py" @'
from forge.autonomous_execution.scheduler import next_eligible_step
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
            objective="Schedule execution steps.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        state=MissionState.EXECUTING,
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def step(
    step_id: str,
    sequence: int,
    depends_on: tuple[str, ...] = (),
) -> MissionStep:
    return MissionStep(
        step_id=step_id,
        plan_id="plan-1",
        sequence=sequence,
        title=step_id,
        description=f"Execute {step_id}.",
        action_kind="read_file",
        depends_on=depends_on,
    )


def test_scheduler_selects_first_eligible_step() -> None:
    plan = MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        objective_summary="Execute steps.",
        completion_criteria=("All steps complete.",),
        steps=(
            step("step-2", 2, ("step-1",)),
            step("step-1", 1),
        ),
    )

    selected = next_eligible_step(
        mission(),
        plan,
        completed_step_ids=frozenset(),
    )

    assert selected is not None
    assert selected.step_id == "step-1"


def test_scheduler_advances_after_completion() -> None:
    plan = MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        objective_summary="Execute steps.",
        completion_criteria=("All steps complete.",),
        steps=(
            step("step-1", 1),
            step("step-2", 2, ("step-1",)),
        ),
    )

    selected = next_eligible_step(
        mission(),
        plan,
        completed_step_ids=frozenset({"step-1"}),
    )

    assert selected is not None
    assert selected.step_id == "step-2"
'@

Write-Utf8NoBom "tests\test_autonomous_execution_planner.py" @'
from forge.autonomous_execution.planner import (
    AutonomousExecutionPlanner,
)
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
            objective="Plan execution.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A2_MODIFY,
            requested_by="Aerion",
        ),
        state=MissionState.EXECUTING,
        granted_authority=AuthorityLevel.A2_MODIFY,
    )


def test_planner_builds_and_selects() -> None:
    step = MissionStep(
        step_id="step-1",
        plan_id="plan-1",
        sequence=1,
        title="Inspect repository",
        description="Inspect repository safely.",
        action_kind="read_file",
    )
    plan = MissionPlan(
        plan_id="plan-1",
        mission_id="mission-1",
        objective_summary="Inspect repository.",
        completion_criteria=("Inspection complete.",),
        steps=(step,),
    )

    planner = AutonomousExecutionPlanner()
    executable = planner.build(plan)
    selection = planner.select_next(
        mission(),
        plan,
        completed_step_ids=frozenset(),
    )

    assert executable.total_steps == 1
    assert selection.step is not None
    assert selection.step.step_id == "step-1"
'@

Write-Host ""
Write-Host "M5.2 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_execution_dependency_graph.py `
    .\tests\test_autonomous_execution_eligibility.py `
    .\tests\test_autonomous_execution_scheduler.py `
    .\tests\test_autonomous_execution_planner.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.2 Package 1 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.2 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short