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

$ExpectedBranch = "feature/m5.6-autonomous-planning-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.6 Package 1 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_planning\graph.py" @'
"""Directed acyclic planning graph."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_planning.errors import PlanningContractError
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningStep,
)


@dataclass(slots=True)
class PlanningGraph:
    """Mutable builder for a deterministic planning DAG."""

    _steps: dict[str, PlanningStep] = field(default_factory=dict)
    _dependencies: dict[str, PlanningDependency] = field(
        default_factory=dict
    )

    def add_step(self, step: PlanningStep) -> None:
        existing = self._steps.get(step.step_id)

        if existing is not None and existing != step:
            raise PlanningContractError(
                f"Conflicting planning step: {step.step_id}"
            )

        self._steps[step.step_id] = step

    def add_dependency(
        self,
        dependency: PlanningDependency,
    ) -> None:
        if dependency.source_step_id not in self._steps:
            raise PlanningContractError(
                "Dependency source step is unknown."
            )

        if dependency.target_step_id not in self._steps:
            raise PlanningContractError(
                "Dependency target step is unknown."
            )

        existing = self._dependencies.get(
            dependency.dependency_id
        )

        if existing is not None and existing != dependency:
            raise PlanningContractError(
                "Conflicting planning dependency: "
                f"{dependency.dependency_id}"
            )

        self._dependencies[
            dependency.dependency_id
        ] = dependency

    def steps(self) -> tuple[PlanningStep, ...]:
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
    ) -> tuple[PlanningDependency, ...]:
        return tuple(
            self._dependencies[key]
            for key in sorted(self._dependencies)
        )

    def prerequisite_ids(
        self,
        step_id: str,
    ) -> tuple[str, ...]:
        if step_id not in self._steps:
            raise PlanningContractError(
                f"Unknown planning step: {step_id}"
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
            raise PlanningContractError(
                f"Unknown planning step: {step_id}"
            )

        values = {
            dependency.source_step_id
            for dependency in self._dependencies.values()
            if dependency.target_step_id == step_id
        }
        return tuple(sorted(values))
'@

Write-Utf8NoBom "forge\autonomous_planning\cycle_detection.py" @'
"""Cycle detection for planning graphs."""

from __future__ import annotations

from forge.autonomous_planning.graph import PlanningGraph


def find_cycle(
    graph: PlanningGraph,
) -> tuple[str, ...] | None:
    """Return one deterministic cycle, if present."""
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

        for prerequisite in adjacency[step_id]:
            cycle = visit(prerequisite)
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


def is_acyclic(graph: PlanningGraph) -> bool:
    """Return whether the planning graph is acyclic."""
    return find_cycle(graph) is None
'@

Write-Utf8NoBom "forge\autonomous_planning\ordering.py" @'
"""Deterministic topological ordering."""

from __future__ import annotations

import heapq

from forge.autonomous_planning.errors import PlanningContractError
from forge.autonomous_planning.graph import PlanningGraph


def topological_order(
    graph: PlanningGraph,
) -> tuple[str, ...]:
    """Return a stable topological ordering."""
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
        raise PlanningContractError(
            "Planning graph contains a dependency cycle."
        )

    return tuple(ordered)
'@

Write-Utf8NoBom "forge\autonomous_planning\eligibility.py" @'
"""Planning-step eligibility evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.graph import PlanningGraph


@dataclass(frozen=True, slots=True)
class StepEligibility:
    """Eligibility result for one planning step."""

    step_id: str
    eligible: bool
    unmet_prerequisites: tuple[str, ...]


def evaluate_step_eligibility(
    *,
    graph: PlanningGraph,
    step_id: str,
    completed_step_ids: tuple[str, ...],
) -> StepEligibility:
    """Evaluate whether all prerequisites are complete."""
    completed = set(completed_step_ids)
    prerequisites = graph.prerequisite_ids(step_id)
    unmet = tuple(
        step
        for step in prerequisites
        if step not in completed
    )

    return StepEligibility(
        step_id=step_id,
        eligible=not unmet,
        unmet_prerequisites=unmet,
    )


def eligible_step_ids(
    *,
    graph: PlanningGraph,
    completed_step_ids: tuple[str, ...],
) -> tuple[str, ...]:
    """Return deterministic currently eligible steps."""
    completed = set(completed_step_ids)
    values: list[str] = []

    for step in graph.steps():
        if step.step_id in completed:
            continue

        result = evaluate_step_eligibility(
            graph=graph,
            step_id=step.step_id,
            completed_step_ids=completed_step_ids,
        )

        if result.eligible:
            values.append(step.step_id)

    return tuple(values)
'@

Write-Utf8NoBom "forge\autonomous_planning\graph_builder.py" @'
"""Planning graph builder from immutable plan contracts."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.cycle_detection import (
    find_cycle,
)
from forge.autonomous_planning.errors import PlanningContractError
from forge.autonomous_planning.graph import PlanningGraph
from forge.autonomous_planning.models import PlanningPlan
from forge.autonomous_planning.ordering import topological_order
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)


@dataclass(frozen=True, slots=True)
class PlanningGraphBuildResult:
    """Built graph and deterministic execution order."""

    graph: PlanningGraph
    ordered_step_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PlanningGraphBuilder:
    """Build and validate a planning graph."""

    policy: AutonomousPlanningPolicy

    def build(
        self,
        plan: PlanningPlan,
    ) -> PlanningGraphBuildResult:
        if len(plan.steps) > self.policy.limits.maximum_steps:
            raise PlanningContractError(
                "Plan exceeds maximum step count."
            )

        if (
            len(plan.dependencies)
            > self.policy.limits.maximum_dependencies
        ):
            raise PlanningContractError(
                "Plan exceeds maximum dependency count."
            )

        graph = PlanningGraph()

        for step in plan.steps:
            graph.add_step(step)

        for dependency in plan.dependencies:
            graph.add_dependency(dependency)

        cycle = find_cycle(graph)

        if (
            cycle is not None
            and self.policy.quality.require_dependency_acyclicity
        ):
            raise PlanningContractError(
                "Planning graph contains cycle: "
                + " -> ".join(cycle)
            )

        ordered = topological_order(graph)

        return PlanningGraphBuildResult(
            graph=graph,
            ordered_step_ids=ordered,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_planning_graph.py" @'
import pytest

from forge.autonomous_planning.errors import (
    PlanningContractError,
)
from forge.autonomous_planning.graph import PlanningGraph
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningStep,
)
from forge.autonomous_planning.states import (
    DependencyKind,
    StepKind,
)


def step(step_id: str, sequence: int) -> PlanningStep:
    return PlanningStep(
        step_id=step_id,
        sequence=sequence,
        name=step_id,
        description="Perform a repository-grounded action.",
        kind=StepKind.ANALYSIS,
    )


def test_graph_returns_prerequisites() -> None:
    graph = PlanningGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))
    graph.add_dependency(
        PlanningDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            kind=DependencyKind.REQUIRES,
            rationale="Step two requires step one.",
        )
    )

    assert graph.prerequisite_ids("step-2") == (
        "step-1",
    )


def test_graph_rejects_unknown_dependency_step() -> None:
    graph = PlanningGraph()
    graph.add_step(step("step-1", 1))

    with pytest.raises(PlanningContractError):
        graph.add_dependency(
            PlanningDependency(
                dependency_id="dependency-1",
                source_step_id="missing",
                target_step_id="step-1",
                kind=DependencyKind.REQUIRES,
                rationale="Invalid dependency.",
            )
        )
'@

Write-Utf8NoBom "tests\test_autonomous_planning_cycle_detection.py" @'
from forge.autonomous_planning.cycle_detection import (
    find_cycle,
    is_acyclic,
)
from forge.autonomous_planning.graph import PlanningGraph
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningStep,
)
from forge.autonomous_planning.states import (
    DependencyKind,
    StepKind,
)


def step(step_id: str, sequence: int) -> PlanningStep:
    return PlanningStep(
        step_id=step_id,
        sequence=sequence,
        name=step_id,
        description="Perform a repository-grounded action.",
        kind=StepKind.ANALYSIS,
    )


def dependency(
    dependency_id: str,
    source: str,
    target: str,
) -> PlanningDependency:
    return PlanningDependency(
        dependency_id=dependency_id,
        source_step_id=source,
        target_step_id=target,
        kind=DependencyKind.REQUIRES,
        rationale="Required ordering.",
    )


def test_cycle_is_detected() -> None:
    graph = PlanningGraph()
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

Write-Utf8NoBom "tests\test_autonomous_planning_ordering.py" @'
import pytest

from forge.autonomous_planning.errors import (
    PlanningContractError,
)
from forge.autonomous_planning.graph import PlanningGraph
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningStep,
)
from forge.autonomous_planning.ordering import (
    topological_order,
)
from forge.autonomous_planning.states import (
    DependencyKind,
    StepKind,
)


def step(step_id: str, sequence: int) -> PlanningStep:
    return PlanningStep(
        step_id=step_id,
        sequence=sequence,
        name=step_id,
        description="Perform a repository-grounded action.",
        kind=StepKind.ANALYSIS,
    )


def test_order_respects_dependencies() -> None:
    graph = PlanningGraph()
    graph.add_step(step("step-2", 2))
    graph.add_step(step("step-1", 1))
    graph.add_dependency(
        PlanningDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            kind=DependencyKind.REQUIRES,
            rationale="Step two requires step one.",
        )
    )

    assert topological_order(graph) == (
        "step-1",
        "step-2",
    )


def test_order_rejects_cycle() -> None:
    graph = PlanningGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))

    for dependency_id, source, target in (
        ("dependency-1", "step-1", "step-2"),
        ("dependency-2", "step-2", "step-1"),
    ):
        graph.add_dependency(
            PlanningDependency(
                dependency_id=dependency_id,
                source_step_id=source,
                target_step_id=target,
                kind=DependencyKind.REQUIRES,
                rationale="Required ordering.",
            )
        )

    with pytest.raises(PlanningContractError):
        topological_order(graph)
'@

Write-Utf8NoBom "tests\test_autonomous_planning_eligibility.py" @'
from forge.autonomous_planning.eligibility import (
    eligible_step_ids,
    evaluate_step_eligibility,
)
from forge.autonomous_planning.graph import PlanningGraph
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningStep,
)
from forge.autonomous_planning.states import (
    DependencyKind,
    StepKind,
)


def step(step_id: str, sequence: int) -> PlanningStep:
    return PlanningStep(
        step_id=step_id,
        sequence=sequence,
        name=step_id,
        description="Perform a repository-grounded action.",
        kind=StepKind.ANALYSIS,
    )


def test_eligibility_requires_completed_prerequisite() -> None:
    graph = PlanningGraph()
    graph.add_step(step("step-1", 1))
    graph.add_step(step("step-2", 2))
    graph.add_dependency(
        PlanningDependency(
            dependency_id="dependency-1",
            source_step_id="step-2",
            target_step_id="step-1",
            kind=DependencyKind.REQUIRES,
            rationale="Step two requires step one.",
        )
    )

    blocked = evaluate_step_eligibility(
        graph=graph,
        step_id="step-2",
        completed_step_ids=(),
    )
    ready = evaluate_step_eligibility(
        graph=graph,
        step_id="step-2",
        completed_step_ids=("step-1",),
    )

    assert not blocked.eligible
    assert ready.eligible
    assert eligible_step_ids(
        graph=graph,
        completed_step_ids=(),
    ) == ("step-1",)
'@

Write-Utf8NoBom "tests\test_autonomous_planning_graph_builder.py" @'
import pytest

from forge.autonomous_planning.errors import (
    PlanningContractError,
)
from forge.autonomous_planning.graph_builder import (
    PlanningGraphBuilder,
)
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.states import (
    DependencyKind,
    StepKind,
)


def step(step_id: str, sequence: int) -> PlanningStep:
    return PlanningStep(
        step_id=step_id,
        sequence=sequence,
        name=step_id,
        description="Perform a repository-grounded action.",
        kind=StepKind.ANALYSIS,
    )


def test_builder_returns_deterministic_order() -> None:
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Plan.",
        steps=(
            step("step-1", 1),
            step("step-2", 2),
        ),
        dependencies=(
            PlanningDependency(
                dependency_id="dependency-1",
                source_step_id="step-2",
                target_step_id="step-1",
                kind=DependencyKind.REQUIRES,
                rationale="Step two requires step one.",
            ),
        ),
    )

    result = PlanningGraphBuilder(
        policy=AutonomousPlanningPolicy()
    ).build(plan)

    assert result.ordered_step_ids == (
        "step-1",
        "step-2",
    )


def test_builder_rejects_cycle() -> None:
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Plan.",
        steps=(
            step("step-1", 1),
            step("step-2", 2),
        ),
        dependencies=(
            PlanningDependency(
                dependency_id="dependency-1",
                source_step_id="step-1",
                target_step_id="step-2",
                kind=DependencyKind.REQUIRES,
                rationale="Required ordering.",
            ),
            PlanningDependency(
                dependency_id="dependency-2",
                source_step_id="step-2",
                target_step_id="step-1",
                kind=DependencyKind.REQUIRES,
                rationale="Required ordering.",
            ),
        ),
    )

    with pytest.raises(PlanningContractError):
        PlanningGraphBuilder(
            policy=AutonomousPlanningPolicy()
        ).build(plan)
'@

Write-Host ""
Write-Host "M5.6 Package 1 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_planning_graph.py `
    .\tests\test_autonomous_planning_cycle_detection.py `
    .\tests\test_autonomous_planning_ordering.py `
    .\tests\test_autonomous_planning_eligibility.py `
    .\tests\test_autonomous_planning_graph_builder.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.6 Package 1 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.6 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short
