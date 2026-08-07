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

$ExpectedBranch = "feature/m5.8-autonomous-agent-runtime"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.8 Package 1 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\mission_runtime\context.py" @'
"""Repository-grounded mission context contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from forge.workspace.models import ProjectType, WorkspaceHealth, WorkspaceStatus


class MissionTechnologyContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    project_type: ProjectType
    technologies: tuple[str, ...] = ()
    primary_language: str | None = None
    framework: str | None = None
    database: str | None = None
    package_manager: str | None = None
    build_system: str | None = None
    test_framework: str | None = None
    docker_enabled: bool = False
    git_enabled: bool = False


class MissionWorkspaceContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace_id: str
    workspace_name: str
    repository_root: str
    status: WorkspaceStatus
    health: WorkspaceHealth
    technology: MissionTechnologyContext


class MissionCapabilitySelection(BaseModel):
    model_config = ConfigDict(frozen=True)

    capability_ids: tuple[str, ...] = ()
    unavailable_capability_ids: tuple[str, ...] = ()
    rationale: tuple[str, ...] = ()
    repository_grounded: bool = True


class MissionEngineeringContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    workspace: MissionWorkspaceContext
    capabilities: MissionCapabilitySelection
    context_references: tuple[str, ...] = Field(default_factory=tuple)
'@

Write-Utf8NoBom "forge\mission_runtime\technology_detection.py" @'
"""Technology context extraction from Forge workspace metadata."""

from __future__ import annotations

from forge.mission_runtime.context import MissionTechnologyContext
from forge.workspace.models import Workspace


def technology_context_from_workspace(
    workspace: Workspace,
) -> MissionTechnologyContext:
    """Convert validated workspace detection into mission context."""
    technologies = tuple(
        sorted(
            {
                technology.strip()
                for technology in workspace.technologies
                if technology.strip()
            },
            key=str.casefold,
        )
    )

    return MissionTechnologyContext(
        project_type=workspace.project_type,
        technologies=technologies,
        primary_language=workspace.primary_language,
        framework=workspace.framework,
        database=workspace.database,
        package_manager=workspace.package_manager,
        build_system=workspace.build_system,
        test_framework=workspace.test_framework,
        docker_enabled=workspace.docker_enabled,
        git_enabled=workspace.git_enabled,
    )
'@

Write-Utf8NoBom "forge\mission_runtime\workspace_context.py" @'
"""Workspace resolution for M5.8 mission runtime."""

from __future__ import annotations

from forge.mission_runtime.context import MissionWorkspaceContext
from forge.mission_runtime.errors import MissionScopeError
from forge.mission_runtime.technology_detection import (
    technology_context_from_workspace,
)
from forge.workspace.manager import WorkspaceManager
from forge.workspace.models import Workspace, WorkspaceStatus


def resolve_workspace(
    *,
    manager: WorkspaceManager,
    workspace_id: str,
    repository_root: str,
) -> Workspace:
    """Resolve and validate the mission workspace."""
    workspace = manager.load(workspace_id)
    expected = workspace.repository_path.resolve()
    actual = manager._validate_path(  # noqa: SLF001
        workspace.repository_path
    )

    if actual != expected:
        raise MissionScopeError(
            "Validated workspace path changed unexpectedly."
        )

    requested = repository_root.strip()

    if requested and actual != workspace.repository_path.__class__(
        requested
    ).resolve():
        raise MissionScopeError(
            "Mission repository does not match workspace repository."
        )

    if workspace.status is WorkspaceStatus.BROKEN:
        raise MissionScopeError(
            "Mission cannot use a broken workspace."
        )

    return workspace


def build_workspace_context(
    workspace: Workspace,
) -> MissionWorkspaceContext:
    """Build immutable mission workspace context."""
    return MissionWorkspaceContext(
        workspace_id=workspace.workspace_id,
        workspace_name=workspace.name,
        repository_root=str(workspace.repository_path.resolve()),
        status=workspace.status,
        health=workspace.health,
        technology=technology_context_from_workspace(
            workspace
        ),
    )
'@

Write-Utf8NoBom "forge\mission_runtime\capability_resolution.py" @'
"""Repository-grounded capability selection for M5.8."""

from __future__ import annotations

from dataclasses import dataclass

from forge.capabilities import CapabilityRegistryQuery
from forge.capabilities.models import CapabilityDefinition
from forge.mission_runtime.context import (
    MissionCapabilitySelection,
    MissionTechnologyContext,
)


def _normalized_signals(
    technology: MissionTechnologyContext,
) -> set[str]:
    values = {
        technology.project_type.value,
        *technology.technologies,
    }

    for value in (
        technology.primary_language,
        technology.framework,
        technology.database,
        technology.package_manager,
        technology.build_system,
        technology.test_framework,
    ):
        if value:
            values.add(value)

    return {
        value.strip().casefold()
        for value in values
        if value.strip()
    }


def _capability_matches(
    definition: CapabilityDefinition,
    signals: set[str],
) -> bool:
    project_types = {
        value.strip().casefold()
        for value in definition.supported_project_types
    }

    tags = {
        value.strip().casefold()
        for value in definition.tags
    }

    return bool(
        project_types.intersection(signals)
        or tags.intersection(signals)
    )


@dataclass(frozen=True, slots=True)
class MissionCapabilityResolver:
    """Select only registered capabilities supported by repository evidence."""

    query: CapabilityRegistryQuery

    def resolve(
        self,
        technology: MissionTechnologyContext,
    ) -> MissionCapabilitySelection:
        signals = _normalized_signals(technology)
        available = {
            definition.capability_id: definition
            for definition in self.query.list_available_capabilities()
        }
        selected = tuple(
            sorted(
                definition.capability_id
                for definition in available.values()
                if _capability_matches(
                    definition,
                    signals,
                )
            )
        )

        rationale = tuple(
            f"{capability_id}: matched repository technology/project evidence."
            for capability_id in selected
        )

        return MissionCapabilitySelection(
            capability_ids=selected,
            unavailable_capability_ids=(),
            rationale=rationale,
            repository_grounded=True,
        )
'@

Write-Utf8NoBom "forge\mission_runtime\context_builder.py" @'
"""Mission engineering-context assembly."""

from __future__ import annotations

from dataclasses import dataclass

from forge.capabilities import CapabilityRegistryQuery
from forge.mission_runtime.capability_resolution import (
    MissionCapabilityResolver,
)
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.models import MissionRequest
from forge.mission_runtime.workspace_context import (
    build_workspace_context,
    resolve_workspace,
)
from forge.workspace.manager import WorkspaceManager


@dataclass(frozen=True, slots=True)
class MissionContextBuilder:
    """Build repository-grounded context for one mission."""

    workspace_manager: WorkspaceManager
    capability_query: CapabilityRegistryQuery

    def build(
        self,
        request: MissionRequest,
    ) -> MissionEngineeringContext:
        workspace = resolve_workspace(
            manager=self.workspace_manager,
            workspace_id=request.workspace_id,
            repository_root=request.repository_root,
        )
        workspace_context = build_workspace_context(
            workspace
        )
        capability_selection = MissionCapabilityResolver(
            self.capability_query
        ).resolve(
            workspace_context.technology
        )

        references = (
            f"workspace:{workspace.workspace_id}",
            f"repository:{workspace_context.repository_root}",
            *(
                f"capability:{capability_id}"
                for capability_id
                in capability_selection.capability_ids
            ),
        )

        return MissionEngineeringContext(
            workspace=workspace_context,
            capabilities=capability_selection,
            context_references=references,
        )
'@

Write-Utf8NoBom "forge\mission_runtime\integration.py" @'
"""Mission runtime integration boundary for repository context."""

from __future__ import annotations

from dataclasses import dataclass

from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.context_builder import MissionContextBuilder
from forge.mission_runtime.models import MissionRequest


@dataclass(frozen=True, slots=True)
class MissionContextIntegration:
    """Stable integration façade for Package 1."""

    builder: MissionContextBuilder

    def resolve(
        self,
        request: MissionRequest,
    ) -> MissionEngineeringContext:
        return self.builder.build(request)
'@

Write-Utf8NoBom "tests\test_mission_runtime_technology_detection.py" @'
from pathlib import Path

from forge.mission_runtime.technology_detection import (
    technology_context_from_workspace,
)
from forge.workspace.models import ProjectType, Workspace


def test_workspace_technology_context_is_deterministic(
    tmp_path: Path,
) -> None:
    workspace = Workspace(
        workspace_id="workspace-1",
        name="ERP",
        repository_path=tmp_path,
        project_type=ProjectType.ERP,
        technologies=["Node", "React", "Node"],
        primary_language="TypeScript",
        framework="React",
        database="PostgreSQL",
        git_enabled=True,
    )

    context = technology_context_from_workspace(
        workspace
    )

    assert context.project_type is ProjectType.ERP
    assert context.technologies == ("Node", "React")
    assert context.database == "PostgreSQL"
'@

Write-Utf8NoBom "tests\test_mission_runtime_capability_resolution.py" @'
from forge.capabilities.models import (
    CapabilityAccessMode,
    CapabilityApprovalPolicy,
    CapabilityAvailabilityScope,
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityEvaluation,
    CapabilityImplementationStatus,
    CapabilityLifecycle,
    CapabilityMaturity,
    CapabilityRegistry,
    CapabilityRegistryGeneration,
    CapabilityRegistryStatistics,
)
from forge.capabilities.query import CapabilityRegistryQuery
from forge.mission_runtime.capability_resolution import (
    MissionCapabilityResolver,
)
from forge.mission_runtime.context import MissionTechnologyContext
from forge.workspace.models import ProjectType


def statistics(
    *,
    total: int,
    available: int,
    implemented: int,
) -> CapabilityRegistryStatistics:
    return CapabilityRegistryStatistics(
        total_capabilities=total,
        available_capabilities=available,
        planned_capabilities=0,
        implemented_capabilities=implemented,
        partially_available_capabilities=0,
        disabled_capabilities=0,
        deprecated_capabilities=0,
        removed_capabilities=0,
        read_only_capabilities=total,
        forge_internal_write_capabilities=0,
        target_mutating_capabilities=0,
        external_side_effect_capabilities=0,
        capabilities_by_category={},
        capabilities_by_maturity={},
        capabilities_by_phase={},
        capabilities_by_milestone={},
    )


def definition(
    capability_id: str,
    *,
    project_types: tuple[str, ...],
) -> CapabilityDefinition:
    return CapabilityDefinition(
        capability_id=capability_id,
        display_name=capability_id,
        description="Test capability.",
        capability_version="1.0",
        forge_version="1.0",
        phase="5",
        milestone="5.8",
        category=CapabilityCategory.INTEGRATION,
        lifecycle=CapabilityLifecycle.AVAILABLE,
        maturity=CapabilityMaturity.STABLE,
        implementation_status=(
            CapabilityImplementationStatus.IMPLEMENTED
        ),
        supported_project_types=project_types,
        access_mode=CapabilityAccessMode.READ_ONLY,
        approval_policy=CapabilityApprovalPolicy.NONE,
        availability_scope=(
            CapabilityAvailabilityScope.PROJECT_TYPE
        ),
    )


def query() -> CapabilityRegistryQuery:
    definitions = (
        definition(
            "erp-capability",
            project_types=("ERP",),
        ),
        definition(
            "flutter-capability",
            project_types=("Flutter",),
        ),
    )

    evaluations = tuple(
        CapabilityEvaluation(
            capability_id=item.capability_id,
            lifecycle=item.lifecycle,
            implementation_status=item.implementation_status,
            available=True,
        )
        for item in definitions
    )

    registry = CapabilityRegistry(
        registry_id="test-registry",
        schema_version="1.0",
        definitions=definitions,
        evaluations=evaluations,
        statistics=statistics(
            total=2,
            available=2,
            implemented=2,
        ),
        generation=CapabilityRegistryGeneration(
            generation_id="test-generation",
            registry_fingerprint="test-fingerprint",
        ),
    )

    return CapabilityRegistryQuery(registry)


def test_resolver_selects_project_capability() -> None:
    selection = MissionCapabilityResolver(
        query()
    ).resolve(
        MissionTechnologyContext(
            project_type=ProjectType.ERP,
            technologies=("React", "Node"),
        )
    )

    assert selection.capability_ids == (
        "erp-capability",
    )
'@

Write-Utf8NoBom "tests\test_mission_runtime_workspace_context.py" @'
import logging
from pathlib import Path

import pytest

from forge.memory import JsonMemoryStore
from forge.mission_runtime.errors import MissionScopeError
from forge.mission_runtime.workspace_context import (
    build_workspace_context,
    resolve_workspace,
)
from forge.workspace.manager import WorkspaceManager
from forge.workspace.models import ProjectType


def manager(tmp_path: Path) -> WorkspaceManager:
    return WorkspaceManager(
        JsonMemoryStore(tmp_path / "memory.json"),
        logging.getLogger("test-mission-runtime"),
    )


def test_workspace_context_resolves_active_repository(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    service = manager(tmp_path)
    workspace = service.register(
        "ERP",
        repository,
        ProjectType.ERP,
    )

    resolved = resolve_workspace(
        manager=service,
        workspace_id=workspace.workspace_id,
        repository_root=str(repository),
    )
    context = build_workspace_context(resolved)

    assert context.workspace_id == workspace.workspace_id
    assert context.technology.project_type is ProjectType.ERP


def test_workspace_context_rejects_scope_mismatch(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    service = manager(tmp_path)
    workspace = service.register(
        "ERP",
        repository,
        ProjectType.ERP,
    )

    with pytest.raises(MissionScopeError):
        resolve_workspace(
            manager=service,
            workspace_id=workspace.workspace_id,
            repository_root=str(other),
        )
'@

Write-Utf8NoBom "tests\test_mission_runtime_context_builder.py" @'
import logging
from pathlib import Path

from forge.capabilities.models import (
    CapabilityRegistry,
    CapabilityRegistryGeneration,
    CapabilityRegistryStatistics,
)
from forge.capabilities.query import CapabilityRegistryQuery
from forge.memory import JsonMemoryStore
from forge.mission_runtime.context_builder import MissionContextBuilder
from forge.mission_runtime.models import MissionRequest
from forge.workspace.manager import WorkspaceManager
from forge.workspace.models import ProjectType


def empty_statistics() -> CapabilityRegistryStatistics:
    return CapabilityRegistryStatistics(
        total_capabilities=0,
        available_capabilities=0,
        planned_capabilities=0,
        implemented_capabilities=0,
        partially_available_capabilities=0,
        disabled_capabilities=0,
        deprecated_capabilities=0,
        removed_capabilities=0,
        read_only_capabilities=0,
        forge_internal_write_capabilities=0,
        target_mutating_capabilities=0,
        external_side_effect_capabilities=0,
        capabilities_by_category={},
        capabilities_by_maturity={},
        capabilities_by_phase={},
        capabilities_by_milestone={},
    )


def test_context_builder_creates_repository_grounded_context(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()

    workspace_manager = WorkspaceManager(
        JsonMemoryStore(tmp_path / "memory.json"),
        logging.getLogger("test-context-builder"),
    )

    workspace = workspace_manager.register(
        "Generic",
        repository,
        ProjectType.GENERIC,
    )

    registry = CapabilityRegistry(
        registry_id="test-registry",
        schema_version="1.0",
        definitions=(),
        evaluations=(),
        statistics=empty_statistics(),
        generation=CapabilityRegistryGeneration(
            generation_id="test-generation",
            registry_fingerprint="test-fingerprint",
        ),
    )

    builder = MissionContextBuilder(
        workspace_manager=workspace_manager,
        capability_query=CapabilityRegistryQuery(
            registry
        ),
    )

    context = builder.build(
        MissionRequest(
            request_id="request-1",
            workspace_id=workspace.workspace_id,
            repository_root=str(repository),
            statement="Inspect repository.",
            requested_by="Aerion",
        )
    )

    assert (
        context.workspace.workspace_id
        == workspace.workspace_id
    )
    assert context.capabilities.repository_grounded
    assert context.context_references[0].startswith(
        "workspace:"
    )
'@

Write-Host ""
Write-Host "M5.8 Package 1 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check forge tests --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check forge tests
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_mission_runtime_technology_detection.py `
    .\tests\test_mission_runtime_capability_resolution.py `
    .\tests\test_mission_runtime_workspace_context.py `
    .\tests\test_mission_runtime_context_builder.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.8 Package 1 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository tests"

Write-Host ""
Write-Host "M5.8 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short