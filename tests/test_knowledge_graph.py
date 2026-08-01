import json
from pathlib import Path

import pytest

from forge.knowledge import KnowledgeEdgeType, KnowledgeNodeType
from tests.knowledge_helpers import graph_service, prepare_inputs, write


def monorepo(path: Path) -> Path:
    write(
        path / "apps" / "web" / "package.json",
        json.dumps({"dependencies": {"react": "19"}}),
    )
    write(path / "apps" / "web" / "src" / "App.tsx")
    write(
        path / "services" / "api" / "package.json",
        json.dumps({"dependencies": {"pg": "8", "express": "5"}}),
    )
    write(path / "services" / "api" / "controllers" / "orders.py")
    write(path / "packages" / "shared" / "package.json", "{}")
    write(path / "packages" / "shared" / "index.ts")
    write(path / "services" / "api" / "migrations" / "001.sql")
    write(path / "k8s" / "deployment.yaml", "kind: Deployment")
    write(path / ".github" / "workflows" / "ci.yml", "name: ci")
    write(path / "README.md", "docs")
    return path


def test_builds_structural_graph_from_persisted_inputs_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = monorepo(tmp_path / "repo")
    prepare_inputs(tmp_path, repository, "workspace-id")

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("graph attempted repository scan")

    monkeypatch.setattr("forge.discovery.scanner.RepositoryDiscoveryScanner.scan", forbidden)
    monkeypatch.setattr("forge.indexing.scanner.ProjectIndexScanner.scan", forbidden)
    result = graph_service(tmp_path).build(repository, "workspace-id", "ERP")
    node_types = {node.node_type for node in result.graph.nodes}
    edge_types = {edge.edge_type for edge in result.graph.edges}

    assert {KnowledgeNodeType.WORKSPACE, KnowledgeNodeType.REPOSITORY} <= node_types
    assert {
        KnowledgeNodeType.APPLICATION,
        KnowledgeNodeType.SERVICE,
        KnowledgeNodeType.LIBRARY,
    } <= node_types
    assert {
        KnowledgeNodeType.FILE,
        KnowledgeNodeType.MANIFEST,
        KnowledgeNodeType.DEPENDENCY,
    } <= node_types
    assert {
        KnowledgeNodeType.FRAMEWORK,
        KnowledgeNodeType.DATABASE,
        KnowledgeNodeType.CI_PIPELINE,
    } <= node_types
    assert KnowledgeEdgeType.DECLARES_DEPENDENCY in edge_types
    assert KnowledgeEdgeType.BELONGS_TO in edge_types
    assert any(
        edge.edge_type is KnowledgeEdgeType.USES_DATABASE
        and edge.source_node_id.startswith("service:")
        for edge in result.graph.edges
    )
    assert result.graph.generation.validation_status == "valid"
    assert all(
        edge.source_node_id in {node.node_id for node in result.graph.nodes}
        and edge.target_node_id in {node.node_id for node in result.graph.nodes}
        for edge in result.graph.edges
    )


@pytest.mark.parametrize(
    "relative",
    [
        "src/main.py",
        "web/App.tsx",
        "server/index.js",
        "lib/main.dart",
        "native/main.cpp",
        "crates/core/lib.rs",
        "cmd/api/main.go",
        "src/main/java/App.java",
        "firmware/px4/main.c",
        "ros2_ws/src/node.cpp",
    ],
)
def test_graph_supports_practical_repository_shapes(tmp_path: Path, relative: str) -> None:
    repository = tmp_path / "repo"
    write(repository / relative)
    prepare_inputs(tmp_path, repository)

    result = graph_service(tmp_path).build(repository)

    assert any(node.path == relative.casefold() for node in result.graph.nodes)
    assert result.graph.generation.statistics.node_count == len(result.graph.nodes)


def test_orphans_are_truthful_for_unassigned_root_files(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    write(repository / "standalone.py")
    write(repository / "package.json", "{}")
    prepare_inputs(tmp_path, repository)

    result = graph_service(tmp_path).build(repository)

    assert result.orphans.unassigned_file_ids
    assert result.orphans.unknown_role_file_ids
    assert result.orphans.unowned_manifest_ids
