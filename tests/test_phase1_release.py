"""Integrated Phase 1 Engineering Runtime release validation."""

import hashlib
import json
import logging
from pathlib import Path

from forge import __version__
from forge.capabilities.catalogue import built_in_catalogue
from forge.capabilities.models import (
    CapabilityImplementationStatus,
    CapabilityRegistryConfiguration,
)
from forge.capabilities.service import CapabilityRegistryService
from forge.capabilities.store import CapabilityRegistryRepository
from forge.configuration.service import ConfigurationService
from forge.diagnostics.models import DiagnosticConfiguration, HealthStatus
from forge.diagnostics.query import DiagnosticQuery
from forge.diagnostics.service import DiagnosticService
from forge.discovery.service import DiscoveryService
from forge.indexing.models import IndexConfiguration
from forge.indexing.service import IndexingService
from forge.indexing.store import ProjectIndexStore
from forge.knowledge.models import KnowledgeGraphConfiguration
from forge.knowledge.service import KnowledgeGraphService
from forge.knowledge.store import KnowledgeGraphRepository
from forge.memory import JsonMemoryStore
from forge.release import build_release_manifest, render_release_manifest
from forge.workspace.manager import WorkspaceManager
from forge.workspace.models import ProjectType


def _logger() -> logging.Logger:
    value = logging.getLogger("phase1-release-test")
    value.handlers = [logging.NullHandler()]
    return value


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _snapshot(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_phase1_end_to_end_is_read_only_and_deterministic(tmp_path: Path) -> None:
    forge_root = tmp_path / "forge-root"
    target = tmp_path / "aerion-fixture"
    memory = tmp_path / "memory"
    reports = tmp_path / "reports"
    (forge_root / "forge").mkdir(parents=True)
    memory.mkdir()
    reports.mkdir()
    _write(
        forge_root / "pyproject.toml",
        '[project]\nname="fixture-forge"\nversion="0.2.0"\nrequires-python=">=3.11"\n',
    )
    _write(target / "pyproject.toml", '[project]\nname="erp-fixture"\nversion="1.0"\n')
    _write(target / "apps" / "web" / "app.py", "value = 1\n")
    _write(target / "services" / "api" / "server.py", "service = True\n")
    _write(target / "lib" / "shared.py", "shared = True\n")
    _write(target / "tests" / "test_app.py", "def test_app():\n    assert True\n")
    _write(target / "config" / "settings.toml", "enabled = true\n")
    _write(target / "migrations" / "001.sql", "create table fixture(id int);\n")
    _write(target / "docs" / "README.md", "# Fixture\n")
    _write(target / "Dockerfile", "FROM scratch\n")
    _write(target / ".github" / "workflows" / "ci.yml", "name: ci\n")
    before = _snapshot(target)
    logger = _logger()
    workspaces = WorkspaceManager(JsonMemoryStore(memory / "workspaces.json"), logger)
    workspace = workspaces.register("ReleaseFixture", target, ProjectType.ERP)
    assert workspaces.select(workspace.workspace_id).workspace_id == workspace.workspace_id

    discovery_service = DiscoveryService(
        JsonMemoryStore(memory / "discovery.json"), reports, logger
    )
    first_discovery = discovery_service.inspect(target, workspace.workspace_id)
    index_service = IndexingService(
        ProjectIndexStore(memory / "index.json"),
        reports,
        logger,
        IndexConfiguration(max_hash_bytes=1024 * 1024, hash_chunk_bytes=1024, max_files=1000),
    )
    first_index = index_service.index(target, workspace.workspace_id)
    graph_service = KnowledgeGraphService(
        memory / "discovery.json",
        ProjectIndexStore(memory / "index.json"),
        KnowledgeGraphRepository(memory / "knowledge_graph.json"),
        reports,
        logger,
        KnowledgeGraphConfiguration(
            max_nodes=10_000,
            max_edges=30_000,
            max_module_depth=2,
            include_directory_nodes=True,
        ),
    )
    first_graph = graph_service.build(target, workspace.workspace_id, workspace.name)
    capabilities = CapabilityRegistryService(
        CapabilityRegistryRepository(memory / "capabilities.json"),
        reports,
        CapabilityRegistryConfiguration(),
    ).build()
    configuration = ConfigurationService(forge_root, memory, reports).resolve(environment={})
    diagnostics = DiagnosticService(forge_root, memory, reports, DiagnosticConfiguration(), logger)
    first_diagnosis = diagnostics.diagnose(workspace.name)
    runtime_health = diagnostics.health()

    second_discovery = discovery_service.inspect(target, workspace.workspace_id)
    second_index = index_service.index(target, workspace.workspace_id)
    second_graph = graph_service.build(target, workspace.workspace_id, workspace.name)
    second_diagnosis = diagnostics.diagnose(workspace.name)

    assert first_discovery.model_dump(exclude={"repository_root"}) == second_discovery.model_dump(
        exclude={"repository_root"}
    )
    assert (
        first_index.project_index.generation.repository_state_fingerprint
        == second_index.project_index.generation.repository_state_fingerprint
    )
    assert (
        first_graph.graph.generation.graph_state_fingerprint
        == second_graph.graph.generation.graph_state_fingerprint
    )
    assert (
        first_diagnosis.snapshot.diagnostic_fingerprint
        == second_diagnosis.snapshot.diagnostic_fingerprint
    )
    query = DiagnosticQuery(second_diagnosis.snapshot)
    assert query.get_result("discovery-index-consistent").status is HealthStatus.HEALTHY
    assert query.get_result("index-graph-consistent").status is HealthStatus.HEALTHY
    assert runtime_health.snapshot.summary.unhealthy_count == 0
    assert capabilities.registry.statistics.available_capabilities == 14
    assert configuration.snapshot.validation.valid
    assert _snapshot(target) == before
    assert not any(path.name in {"memory", "reports"} for path in target.iterdir())
    assert str(target) not in (reports / "PROJECT.json").read_text(encoding="utf-8")
    assert str(target) not in (reports / "PROJECT_SUMMARY.md").read_text(encoding="utf-8")


def test_release_inventory_version_and_phase2_boundary() -> None:
    manifest = build_release_manifest()
    catalogue = built_in_catalogue()
    assert __version__ == "0.2.0" == manifest.version
    assert len(catalogue) == 31
    assert len(manifest.implemented_capability_ids) == 8
    assert len(manifest.planned_capability_ids) == 23
    assert "phase-validation-release" in manifest.implemented_capability_ids
    assert "mission-planning" in manifest.planned_capability_ids
    assert set(manifest.implemented_capability_ids).isdisjoint(manifest.planned_capability_ids)
    assert set(manifest.implemented_capability_ids) | set(manifest.planned_capability_ids) == {
        item.capability_id for item in catalogue
    }

    current_implemented = {
        item.capability_id
        for item in catalogue
        if item.implementation_status is CapabilityImplementationStatus.IMPLEMENTED
    }
    assert "mission-planning" in current_implemented
    assert len(manifest.schemas) == 7
    assert len(manifest.persistence_files) == 7


def test_release_manifest_is_deterministic_and_git_independent() -> None:
    first = render_release_manifest()
    second = render_release_manifest()
    third = render_release_manifest()
    assert first == second == third
    assert "pending" in first
    assert "7e3879d" in first
    assert "forge-v0.2.0" in first
    assert "conditional_pass" in first


def test_release_documents_and_command_inventory_exist() -> None:
    root = Path(__file__).resolve().parents[1]
    required = (
        "docs/audits/PHASE_1_RELEASE_VALIDATION.md",
        "docs/contracts/PHASE_1_ENGINEERING_RUNTIME_CONTRACT.md",
        "docs/releases/AERION_FORGE_V0_2_RELEASE_NOTES.md",
        "reports/latest/PHASE_1_RELEASE_MANIFEST.json",
    )
    assert all((root / path).is_file() for path in required)
    manifest = build_release_manifest()
    persisted_manifest = json.loads(
        (root / "reports/latest/PHASE_1_RELEASE_MANIFEST.json").read_text(encoding="utf-8")
    )
    assert persisted_manifest == manifest.model_dump(mode="json")
    assert manifest.cli_command_families == (
        "capabilities",
        "capability",
        "config",
        "diagnose",
        "graph",
        "health",
        "index",
        "inspect",
        "workspace",
    )
