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