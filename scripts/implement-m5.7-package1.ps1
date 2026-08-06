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

$ExpectedBranch = "feature/m5.7-autonomous-execution-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.7 Package 1 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_execution_v2\graph.py" @'
"""Dependency graph for M5.7 autonomous execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionStep,
)


@dataclass(slots=True)
class ExecutionGraph:
    """Mutable deterministic execution graph."""

    _steps: dict[str, ExecutionStep] = field(
        default_factory=dict
    )
    _dependencies: dict[str, ExecutionDependency] = field(
        default_factory=dict
    )

    def add_step(self, step: ExecutionStep) -> None:
        existing = self._steps.get(step.step_id)

        if existing is not None and existing != step:
            raise ExecutionContractError(
                f"Conflicting execution step: {step.step_id}"
            )

        self._steps[step.step_id] = step

    def add_dependency(
        self,
        dependency: ExecutionDependency,
    ) -> None:
        if dependency.source_step_id not in self._steps:
            raise ExecutionContractError(
                "Dependency source step is unknown."
            )

        if dependency.target_step_id not in self._steps:
            raise ExecutionContractError(
                "Dependency target step is unknown."
            )

        existing = self._dependencies.get(
            dependency.dependency_id
        )

        if existing is not None and existing != dependency:
            raise ExecutionContractError(
                "Conflicting execution dependency: "
                f"{dependency.dependency_id}"
            )

        self._dependencies[
            dependency.dependency_id
        ] = dependency

    def steps(self) -> tuple[ExecutionStep, ...]:
        return tuple(
            sorted(
                self._steps.values(),
                key=lambda item: (
                    item.sequence,
                    item.step_id,
                ),
            )
        )

    def dependencies(
        self,
    ) -> tuple[ExecutionDependency, ...]:
        return tuple(
            self._dependencies[key]
            for key in sorted(self._dependencies)
        )

    def prerequisite_ids(
        self,
        step_id: str,
    ) -> tuple[str, ...]:
        if step_id not in self._steps:
            raise ExecutionContractError(
                f"Unknown execution step: {step_id}"
            )

        values = {
            dependency.target_step_id
            for dependency in self._dependencies.values()
            if dependency.source_step_id == step_id
        }
        return tuple(sorted(values))

    def dependent_ids(
        self,
        step_id: str,
    ) -> tuple[str, ...]:
        if step_id not in self._steps:
            raise ExecutionContractError(
                f"Unknown execution step: {step_id}"
            )

        values = {
            dependency.source_step_id
            for dependency in self._dependencies.values()
            if dependency.target_step_id == step_id
        }
        return tuple(sorted(values))
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\cycle_detection.py" @'
"""Cycle detection for M5.7 execution graphs."""

from __future__ import annotations

from forge.autonomous_execution_v2.graph import ExecutionGraph


def find_cycle(
    graph: ExecutionGraph,
) -> tuple[str, ...] | None:
    """Return one deterministic dependency cycle."""
    adjacency = {
        step.step_id: graph.prerequisite_ids(step.step_id)
        for step in graph.steps()
    }
    visited: set[str] = set()
    active: list[str] = []
    active_set: set[str] = set()

    def visit(step_id: str) -> tuple[str, ...] | None:
        if step_id in active_set:
            start = active.index(step_id)
            return tuple([*active[start:], step_id])

        if step_id in visited:
            return None

        active.append(step_id)
        active_set.add(step_id)

        for prerequisite_id in adjacency[step_id]:
            cycle = visit(prerequisite_id)

            if cycle is not None:
                return cycle

        active.pop()
        active_set.remove(step_id)
        visited.add(step_id)
        return None

    for step_id in sorted(adjacency):
        cycle = visit(step_id)

        if cycle is not None:
            return cycle

    return None


def is_acyclic(graph: ExecutionGraph) -> bool:
    """Return whether the execution graph is acyclic."""
    return find_cycle(graph) is None
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\ordering.py" @'
"""Deterministic topological ordering for M5.7."""

from __future__ import annotations

import heapq

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph


def topological_order(
    graph: ExecutionGraph,
) -> tuple[str, ...]:
    """Return a stable dependency-respecting order."""
    steps = {
        step.step_id: step
        for step in graph.steps()
    }
    indegree = {
        step_id: 0
        for step_id in steps
    }
    dependents: dict[str, list[str]] = {
        step_id: []
        for step_id in steps
    }

    for dependency in graph.dependencies():
        indegree[dependency.source_step_id] += 1
        dependents[dependency.target_step_id].append(
            dependency.source_step_id
        )

    ready: list[tuple[int, str]] = []

    for step_id, degree in indegree.items():
        if degree == 0:
            heapq.heappush(
                ready,
                (
                    steps[step_id].sequence,
                    step_id,
                ),
            )

    ordered: list[str] = []

    while ready:
        _, step_id = heapq.heappop(ready)
        ordered.append(step_id)

        for dependent_id in sorted(
            dependents[step_id]
        ):
            indegree[dependent_id] -= 1

            if indegree[dependent_id] == 0:
                heapq.heappush(
                    ready,
                    (
                        steps[dependent_id].sequence,
                        dependent_id,
                    ),
                )

    if len(ordered) != len(steps):
        raise ExecutionContractError(
            "Execution graph contains a dependency cycle."
        )

    return tuple(ordered)
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\eligibility.py" @'
"""Execution-step eligibility evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.states import (
    ExecutionStepState,
)


@dataclass(frozen=True, slots=True)
class ExecutionEligibility:
    """Eligibility result for one execution step."""

    step_id: str
    eligible: bool
    unmet_prerequisites: tuple[str, ...]
    blocking_steps: tuple[str, ...]


def evaluate_execution_eligibility(
    *,
    graph: ExecutionGraph,
    step_id: str,
    step_states: dict[str, ExecutionStepState],
) -> ExecutionEligibility:
    """Evaluate whether a step may be scheduled."""
    prerequisites = graph.prerequisite_ids(step_id)
    unmet = tuple(
        prerequisite_id
        for prerequisite_id in prerequisites
        if step_states.get(prerequisite_id)
        is not ExecutionStepState.SUCCEEDED
    )
    blocking = tuple(
        prerequisite_id
        for prerequisite_id in prerequisites
        if step_states.get(prerequisite_id)
        in {
            ExecutionStepState.FAILED,
            ExecutionStepState.BLOCKED,
            ExecutionStepState.CANCELLED,
        }
    )

    return ExecutionEligibility(
        step_id=step_id,
        eligible=not unmet,
        unmet_prerequisites=unmet,
        blocking_steps=blocking,
    )


def eligible_execution_step_ids(
    *,
    graph: ExecutionGraph,
    step_states: dict[str, ExecutionStepState],
) -> tuple[str, ...]:
    """Return deterministic currently eligible step IDs."""
    values: list[str] = []

    for step in graph.steps():
        state = step_states.get(
            step.step_id,
            step.state,
        )

        if state in {
            ExecutionStepState.SUCCEEDED,
            ExecutionStepState.RUNNING,
            ExecutionStepState.SKIPPED,
            ExecutionStepState.CANCELLED,
        }:
            continue

        result = evaluate_execution_eligibility(
            graph=graph,
            step_id=step.step_id,
            step_states=step_states,
        )

        if result.eligible:
            values.append(step.step_id)

    return tuple(values)
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\scheduler.py" @'
"""Deterministic scheduler for M5.7 execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.eligibility import (
    eligible_execution_step_ids,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.ordering import topological_order
from forge.autonomous_execution_v2.states import (
    ExecutionStepState,
)


@dataclass(frozen=True, slots=True)
class ExecutionSchedule:
    """Current execution scheduling decision."""

    ordered_step_ids: tuple[str, ...]
    eligible_step_ids: tuple[str, ...]
    next_step_id: str | None


def build_execution_schedule(
    *,
    graph: ExecutionGraph,
    step_states: dict[str, ExecutionStepState],
) -> ExecutionSchedule:
    """Build deterministic execution schedule."""
    ordered = topological_order(graph)
    eligible = set(
        eligible_execution_step_ids(
            graph=graph,
            step_states=step_states,
        )
    )
    eligible_ordered = tuple(
        step_id
        for step_id in ordered
        if step_id in eligible
    )

    return ExecutionSchedule(
        ordered_step_ids=ordered,
        eligible_step_ids=eligible_ordered,
        next_step_id=(
            eligible_ordered[0]
            if eligible_ordered
            else None
        ),
    )
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\graph_builder.py" @'
"""Execution graph construction from execution runs."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.cycle_detection import (
    find_cycle,
)
from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.models import ExecutionRun
from forge.autonomous_execution_v2.ordering import (
    topological_order,
)
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)


@dataclass(frozen=True, slots=True)
class ExecutionGraphBuildResult:
    """Built graph and deterministic order."""

    graph: ExecutionGraph
    ordered_step_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutionGraphBuilder:
    """Build and validate an execution graph."""

    policy: AutonomousExecutionV2Policy

    def build(
        self,
        run: ExecutionRun,
    ) -> ExecutionGraphBuildResult:
        if len(run.steps) > self.policy.limits.maximum_steps:
            raise ExecutionContractError(
                "Execution run exceeds maximum step count."
            )

        graph = ExecutionGraph()

        for step in run.steps:
            graph.add_step(step)

        for dependency in run.dependencies:
            graph.add_dependency(dependency)

        cycle = find_cycle(graph)

        if cycle is not None:
            raise ExecutionContractError(
                "Execution graph contains cycle: "
                + " -> ".join(cycle)
            )

        return ExecutionGraphBuildResult(
            graph=graph,
            ordered_step_ids=topological_order(graph),
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_graph.py" @'
import pytest

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionStep,
)


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=step_id,
        description="Execute a repository-grounded action.",
    )


def test_graph_returns_prerequisites() -> None:
    graph = ExecutionGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))
    graph.add_dependency(
        ExecutionDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            rationale="Step two requires step one.",
        )
    )

    assert graph.prerequisite_ids("step-2") == (
        "step-1",
    )


def test_graph_rejects_unknown_dependency_step() -> None:
    graph = ExecutionGraph()
    graph.add_step(step("step-1", 1))

    with pytest.raises(ExecutionContractError):
        graph.add_dependency(
            ExecutionDependency(
                dependency_id="dependency-1",
                source_step_id="missing",
                target_step_id="step-1",
                rationale="Invalid dependency.",
            )
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_cycle_detection.py" @'
from forge.autonomous_execution_v2.cycle_detection import (
    find_cycle,
    is_acyclic,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionStep,
)


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=step_id,
        description="Execute a repository-grounded action.",
    )


def dependency(
    dependency_id: str,
    source: str,
    target: str,
) -> ExecutionDependency:
    return ExecutionDependency(
        dependency_id=dependency_id,
        source_step_id=source,
        target_step_id=target,
        rationale="Required ordering.",
    )


def test_cycle_is_detected() -> None:
    graph = ExecutionGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))
    graph.add_dependency(
        dependency(
            "dependency-1",
            "step-1",
            "step-2",
        )
    )
    graph.add_dependency(
        dependency(
            "dependency-2",
            "step-2",
            "step-1",
        )
    )

    assert not is_acyclic(graph)
    assert find_cycle(graph) is not None
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_ordering.py" @'
import pytest

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionStep,
)
from forge.autonomous_execution_v2.ordering import (
    topological_order,
)


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=step_id,
        description="Execute a repository-grounded action.",
    )


def test_order_respects_dependencies() -> None:
    graph = ExecutionGraph()
    graph.add_step(step("step-2", 2))
    graph.add_step(step("step-1", 1))
    graph.add_dependency(
        ExecutionDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            rationale="Step two requires step one.",
        )
    )

    assert topological_order(graph) == (
        "step-1",
        "step-2",
    )


def test_order_rejects_cycle() -> None:
    graph = ExecutionGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))

    for dependency_id, source, target in (
        ("dependency-1", "step-1", "step-2"),
        ("dependency-2", "step-2", "step-1"),
    ):
        graph.add_dependency(
            ExecutionDependency(
                dependency_id=dependency_id,
                source_step_id=source,
                target_step_id=target,
                rationale="Required ordering.",
            )
        )

    with pytest.raises(ExecutionContractError):
        topological_order(graph)
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_eligibility.py" @'
from forge.autonomous_execution_v2.eligibility import (
    eligible_execution_step_ids,
    evaluate_execution_eligibility,
)
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionStep,
)
from forge.autonomous_execution_v2.states import (
    ExecutionStepState,
)


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=step_id,
        description="Execute a repository-grounded action.",
    )


def test_eligibility_requires_completed_prerequisite() -> None:
    graph = ExecutionGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))
    graph.add_dependency(
        ExecutionDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            rationale="Step two requires step one.",
        )
    )

    blocked = evaluate_execution_eligibility(
        graph=graph,
        step_id="step-2",
        step_states={
            "step-1": ExecutionStepState.PENDING,
        },
    )
    ready = evaluate_execution_eligibility(
        graph=graph,
        step_id="step-2",
        step_states={
            "step-1": ExecutionStepState.SUCCEEDED,
        },
    )

    assert not blocked.eligible
    assert ready.eligible
    assert eligible_execution_step_ids(
        graph=graph,
        step_states={},
    ) == ("step-1",)
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_scheduler.py" @'
from forge.autonomous_execution_v2.graph import ExecutionGraph
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionStep,
)
from forge.autonomous_execution_v2.scheduler import (
    build_execution_schedule,
)
from forge.autonomous_execution_v2.states import (
    ExecutionStepState,
)


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=step_id,
        description="Execute a repository-grounded action.",
    )


def test_scheduler_selects_first_eligible_step() -> None:
    graph = ExecutionGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))
    graph.add_dependency(
        ExecutionDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            rationale="Step two requires step one.",
        )
    )

    schedule = build_execution_schedule(
        graph=graph,
        step_states={
            "step-1": ExecutionStepState.PENDING,
            "step-2": ExecutionStepState.PENDING,
        },
    )

    assert schedule.next_step_id == "step-1"
    assert schedule.eligible_step_ids == ("step-1",)
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_graph_builder.py" @'
import pytest

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.graph_builder import (
    ExecutionGraphBuilder,
)
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=step_id,
        description="Execute a repository-grounded action.",
    )


def run(
    dependencies: tuple[ExecutionDependency, ...],
) -> ExecutionRun:
    return ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        steps=(
            step("step-1", 1),
            step("step-2", 2),
        ),
        dependencies=dependencies,
    )


def test_builder_returns_deterministic_order() -> None:
    result = ExecutionGraphBuilder(
        policy=AutonomousExecutionV2Policy()
    ).build(
        run(
            (
                ExecutionDependency(
                    dependency_id="dependency-1",
                    source_step_id="step-2",
                    target_step_id="step-1",
                    rationale="Step two requires step one.",
                ),
            )
        )
    )

    assert result.ordered_step_ids == (
        "step-1",
        "step-2",
    )


def test_builder_rejects_cycle() -> None:
    dependencies = (
        ExecutionDependency(
            dependency_id="dependency-1",
            source_step_id="step-1",
            target_step_id="step-2",
            rationale="Required ordering.",
        ),
        ExecutionDependency(
            dependency_id="dependency-2",
            source_step_id="step-2",
            target_step_id="step-1",
            rationale="Required ordering.",
        ),
    )

    with pytest.raises(ExecutionContractError):
        ExecutionGraphBuilder(
            policy=AutonomousExecutionV2Policy()
        ).build(run(dependencies))
'@

Write-Host ""
Write-Host "M5.7 Package 1 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_execution_v2_graph.py `
    .\tests\test_autonomous_execution_v2_cycle_detection.py `
    .\tests\test_autonomous_execution_v2_ordering.py `
    .\tests\test_autonomous_execution_v2_eligibility.py `
    .\tests\test_autonomous_execution_v2_scheduler.py `
    .\tests\test_autonomous_execution_v2_graph_builder.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.7 Package 1 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository tests"

Write-Host ""
Write-Host "M5.7 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short