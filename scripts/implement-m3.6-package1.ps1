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

Write-Utf8NoBom "forge\mission_orchestration\stages.py" @'
"""Built-in stage definitions for M3.6 Mission Orchestration."""

from __future__ import annotations

from forge.mission_orchestration.models import StageDefinition, StageType


def builtin_stage_definitions() -> tuple[StageDefinition, ...]:
    """Return the deterministic built-in mission workflow stages."""
    return (
        StageDefinition(
            stage_id="mission_validation",
            stage_type=StageType.MISSION_VALIDATION,
            name="Mission validation",
        ),
        StageDefinition(
            stage_id="execution_request",
            stage_type=StageType.EXECUTION_REQUEST,
            name="Execution request",
            dependencies=("mission_validation",),
        ),
        StageDefinition(
            stage_id="safe_change_plan",
            stage_type=StageType.SAFE_CHANGE_PLAN,
            name="Safe change plan",
            dependencies=("execution_request",),
        ),
        StageDefinition(
            stage_id="impact_assessment",
            stage_type=StageType.IMPACT_ASSESSMENT,
            name="Impact assessment",
            dependencies=("safe_change_plan",),
        ),
        StageDefinition(
            stage_id="approval_gate",
            stage_type=StageType.APPROVAL_GATE,
            name="Approval gate",
            dependencies=("impact_assessment",),
            approval_required=True,
        ),
        StageDefinition(
            stage_id="safe_edit_dry_run",
            stage_type=StageType.SAFE_EDIT_DRY_RUN,
            name="Safe edit dry-run",
            dependencies=("approval_gate",),
        ),
        StageDefinition(
            stage_id="safe_edit_apply",
            stage_type=StageType.SAFE_EDIT_APPLY,
            name="Safe edit apply",
            dependencies=("safe_edit_dry_run",),
            approval_required=True,
        ),
        StageDefinition(
            stage_id="validation",
            stage_type=StageType.VALIDATION,
            name="Validation",
            dependencies=("safe_edit_apply",),
        ),
        StageDefinition(
            stage_id="autonomous_repair",
            stage_type=StageType.AUTONOMOUS_REPAIR,
            name="Autonomous repair",
            dependencies=("validation",),
            optional=True,
            max_attempts=3,
        ),
        StageDefinition(
            stage_id="final_validation",
            stage_type=StageType.FINAL_VALIDATION,
            name="Final validation",
            dependencies=("validation", "autonomous_repair"),
        ),
        StageDefinition(
            stage_id="mission_reporting",
            stage_type=StageType.MISSION_REPORTING,
            name="Mission reporting",
            dependencies=("final_validation",),
        ),
    )
'@

Write-Utf8NoBom "forge\mission_orchestration\registry.py" @'
"""Deterministic stage registry for M3.6 Mission Orchestration."""

from __future__ import annotations

from forge.mission_orchestration.errors import (
    MissionStageConflictError,
    MissionStageNotFoundError,
)
from forge.mission_orchestration.models import StageDefinition, StageType
from forge.mission_orchestration.stages import builtin_stage_definitions


class MissionStageRegistry:
    """Register and resolve orchestration stages deterministically."""

    def __init__(self) -> None:
        self._stages: dict[str, StageDefinition] = {}
        self._types: dict[StageType, str] = {}

    def register(self, definition: StageDefinition) -> None:
        """Register one unique stage definition."""
        if definition.stage_id in self._stages:
            raise MissionStageConflictError(
                f"stage already registered: {definition.stage_id}"
            )
        if definition.stage_type in self._types:
            raise MissionStageConflictError(
                f"stage type already registered: {definition.stage_type}"
            )
        self._stages[definition.stage_id] = definition
        self._types[definition.stage_type] = definition.stage_id

    def get(self, stage_id: str) -> StageDefinition:
        """Resolve a stage by identifier."""
        try:
            return self._stages[stage_id]
        except KeyError as exc:
            raise MissionStageNotFoundError(
                f"stage not registered: {stage_id}"
            ) from exc

    def get_by_type(self, stage_type: StageType) -> StageDefinition:
        """Resolve a stage by type."""
        try:
            return self.get(self._types[stage_type])
        except KeyError as exc:
            raise MissionStageNotFoundError(
                f"stage type not registered: {stage_type}"
            ) from exc

    def list(self) -> tuple[StageDefinition, ...]:
        """Return registered stages in deterministic order."""
        return tuple(
            self._stages[stage_id]
            for stage_id in sorted(self._stages)
        )

    @classmethod
    def with_builtins(cls) -> MissionStageRegistry:
        """Return a registry populated with all built-in stages."""
        registry = cls()
        for definition in builtin_stage_definitions():
            registry.register(definition)
        return registry
'@

Write-Utf8NoBom "forge\mission_orchestration\workflow.py" @'
"""Workflow graph construction and validation for M3.6."""

from __future__ import annotations

from collections import defaultdict, deque

from forge.mission_orchestration.errors import MissionDependencyError
from forge.mission_orchestration.identifiers import workflow_identifier
from forge.mission_orchestration.models import (
    MissionRequest,
    MissionWorkflow,
    StageDefinition,
)
from forge.mission_orchestration.policies import MissionOrchestrationPolicy
from forge.mission_orchestration.registry import MissionStageRegistry


def topological_order(
    stages: tuple[StageDefinition, ...],
) -> tuple[StageDefinition, ...]:
    """Return deterministic topological order or reject cycles."""
    by_id = {stage.stage_id: stage for stage in stages}
    indegree = {stage.stage_id: 0 for stage in stages}
    dependants: dict[str, list[str]] = defaultdict(list)

    for stage in stages:
        for dependency in stage.dependencies:
            if dependency not in by_id:
                raise MissionDependencyError(
                    f"unknown dependency {dependency} for {stage.stage_id}"
                )
            indegree[stage.stage_id] += 1
            dependants[dependency].append(stage.stage_id)

    ready = deque(sorted(
        stage_id
        for stage_id, count in indegree.items()
        if count == 0
    ))
    ordered: list[StageDefinition] = []

    while ready:
        stage_id = ready.popleft()
        ordered.append(by_id[stage_id])
        for dependant in sorted(dependants[stage_id]):
            indegree[dependant] -= 1
            if indegree[dependant] == 0:
                ready.append(dependant)

    if len(ordered) != len(stages):
        raise MissionDependencyError("workflow contains a dependency cycle")

    return tuple(ordered)


def validate_required_stages(
    stages: tuple[StageDefinition, ...],
    policy: MissionOrchestrationPolicy,
) -> None:
    """Ensure all policy-required stages are present."""
    present = {stage.stage_type for stage in stages}
    missing = [stage_type.value for stage_type in policy.required_stages if stage_type not in present]
    if missing:
        raise MissionDependencyError(
            f"workflow is missing required stages: {', '.join(sorted(missing))}"
        )


def build_default_workflow(
    request: MissionRequest,
    *,
    registry: MissionStageRegistry | None = None,
    policy: MissionOrchestrationPolicy | None = None,
) -> MissionWorkflow:
    """Build the default deterministic workflow for one mission."""
    active_registry = registry or MissionStageRegistry.with_builtins()
    active_policy = policy or MissionOrchestrationPolicy()

    stages = active_registry.list()
    validate_required_stages(stages, active_policy)
    ordered = topological_order(stages)

    workflow_id = workflow_identifier(
        {
            "mission_id": request.mission_id,
            "stages": [
                {
                    "stage_id": stage.stage_id,
                    "stage_type": stage.stage_type.value,
                    "dependencies": stage.dependencies,
                    "approval_required": stage.approval_required,
                    "optional": stage.optional,
                    "max_attempts": stage.max_attempts,
                }
                for stage in ordered
            ],
        }
    )
    return MissionWorkflow(
        workflow_id=workflow_id,
        mission_id=request.mission_id,
        stages=ordered,
    )
'@

Write-Utf8NoBom "tests\test_mission_orchestration_stages.py" @'
from forge.mission_orchestration.models import StageType
from forge.mission_orchestration.stages import builtin_stage_definitions


def test_builtin_stages_are_complete() -> None:
    stages = builtin_stage_definitions()
    types = {stage.stage_type for stage in stages}

    assert StageType.MISSION_VALIDATION in types
    assert StageType.SAFE_EDIT_APPLY in types
    assert StageType.AUTONOMOUS_REPAIR in types
    assert StageType.MISSION_REPORTING in types


def test_apply_and_approval_gate_require_approval() -> None:
    stages = {stage.stage_id: stage for stage in builtin_stage_definitions()}

    assert stages["approval_gate"].approval_required is True
    assert stages["safe_edit_apply"].approval_required is True
'@

Write-Utf8NoBom "tests\test_mission_orchestration_registry.py" @'
import pytest

from forge.mission_orchestration.errors import (
    MissionStageConflictError,
    MissionStageNotFoundError,
)
from forge.mission_orchestration.models import StageDefinition, StageType
from forge.mission_orchestration.registry import MissionStageRegistry


def test_builtin_registry_contains_all_stages() -> None:
    registry = MissionStageRegistry.with_builtins()

    assert len(registry.list()) == 11
    assert registry.get("mission_validation").stage_type is StageType.MISSION_VALIDATION


def test_duplicate_stage_id_is_rejected() -> None:
    registry = MissionStageRegistry()
    definition = StageDefinition(
        stage_id="validate",
        stage_type=StageType.MISSION_VALIDATION,
        name="Validate",
    )
    registry.register(definition)

    with pytest.raises(MissionStageConflictError):
        registry.register(definition)


def test_missing_stage_is_rejected() -> None:
    with pytest.raises(MissionStageNotFoundError):
        MissionStageRegistry().get("missing")
'@

Write-Utf8NoBom "tests\test_mission_orchestration_workflow.py" @'
import pytest

from forge.mission_orchestration.errors import MissionDependencyError
from forge.mission_orchestration.models import (
    MissionRequest,
    StageDefinition,
    StageType,
)
from forge.mission_orchestration.workflow import (
    build_default_workflow,
    topological_order,
)


def request() -> MissionRequest:
    return MissionRequest(
        mission_id="mission-1",
        repository_root=".",
        objective="Build feature",
        requested_paths=("forge/app.py",),
    )


def test_default_workflow_is_deterministic() -> None:
    first = build_default_workflow(request())
    second = build_default_workflow(request())

    assert first.workflow_id == second.workflow_id
    assert first.stages[0].stage_id == "mission_validation"
    assert first.stages[-1].stage_id == "mission_reporting"


def test_topological_order_respects_dependencies() -> None:
    stages = (
        StageDefinition(
            stage_id="b",
            stage_type=StageType.SAFE_CHANGE_PLAN,
            name="B",
            dependencies=("a",),
        ),
        StageDefinition(
            stage_id="a",
            stage_type=StageType.MISSION_VALIDATION,
            name="A",
        ),
    )

    ordered = topological_order(stages)

    assert tuple(stage.stage_id for stage in ordered) == ("a", "b")


def test_cycle_is_rejected() -> None:
    stages = (
        StageDefinition(
            stage_id="a",
            stage_type=StageType.MISSION_VALIDATION,
            name="A",
            dependencies=("b",),
        ),
        StageDefinition(
            stage_id="b",
            stage_type=StageType.SAFE_CHANGE_PLAN,
            name="B",
            dependencies=("a",),
        ),
    )

    with pytest.raises(MissionDependencyError):
        topological_order(stages)
'@

Write-Host ""
Write-Host "M3.6 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_mission_orchestration_stages.py `
    .\tests\test_mission_orchestration_registry.py `
    .\tests\test_mission_orchestration_workflow.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.6 PACKAGE 1 COMPLETE" -ForegroundColor Green
git status --short
