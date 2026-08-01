from pathlib import Path

import pytest

from forge.indexing import ProjectIndex
from forge.knowledge import (
    KnowledgeGraph,
    KnowledgeGraphCorruptionError,
    KnowledgeGraphInputMismatchError,
    KnowledgeGraphLimitExceededError,
    KnowledgeGraphValidationError,
)
from forge.knowledge.service import KnowledgeGraphService
from forge.knowledge.validator import KnowledgeGraphValidator
from tests.knowledge_helpers import graph_service, prepare_inputs, write


def baseline(
    tmp_path: Path,
) -> tuple[Path, KnowledgeGraphService, KnowledgeGraph, ProjectIndex]:
    repository = tmp_path / "repo"
    write(repository / "src" / "app.py")
    prepare_inputs(tmp_path, repository)
    service = graph_service(tmp_path)
    result = service.build(repository)
    project_index = service.index_store.load().repositories[
        result.graph.generation.repository_identity
    ]
    return repository, service, result.graph, project_index


@pytest.mark.parametrize(
    "mutation, expected",
    [
        ("duplicate_node", "duplicate node ID"),
        ("duplicate_edge", "duplicate edge ID"),
        ("missing_source", "missing edge source"),
        ("missing_target", "missing edge target"),
        ("self_edge", "forbidden self-edge"),
        ("repository", "repository identity mismatch"),
        ("index", "source index state mismatch"),
        ("absolute", "absolute portable path"),
        ("statistics", "graph statistics mismatch"),
    ],
)
def test_validator_rejects_invalid_graphs(tmp_path: Path, mutation: str, expected: str) -> None:
    _, _, graph, project_index = baseline(tmp_path)
    if mutation == "duplicate_node":
        graph.nodes.append(graph.nodes[0])
    elif mutation == "duplicate_edge":
        graph.edges.append(graph.edges[0])
    elif mutation == "missing_source":
        graph.edges[0] = graph.edges[0].model_copy(update={"source_node_id": "missing"})
    elif mutation == "missing_target":
        graph.edges[0] = graph.edges[0].model_copy(update={"target_node_id": "missing"})
    elif mutation == "self_edge":
        graph.edges[0] = graph.edges[0].model_copy(
            update={"target_node_id": graph.edges[0].source_node_id}
        )
    elif mutation == "repository":
        graph.generation = graph.generation.model_copy(update={"repository_identity": "wrong"})
    elif mutation == "index":
        graph.generation = graph.generation.model_copy(
            update={"source_index_state_fingerprint": "wrong"}
        )
    elif mutation == "absolute":
        graph.nodes[0] = graph.nodes[0].model_copy(update={"path": "C:/secret/path"})
    else:
        graph.generation.statistics.node_count += 1

    result = KnowledgeGraphValidator().validate(graph, project_index)

    assert not result.valid
    assert any(expected in error for error in result.errors)


def test_validation_failure_and_limit_preserve_previous_graph(tmp_path: Path) -> None:
    repository, service, _, _ = baseline(tmp_path)
    path = tmp_path / "memory" / "knowledge_graph.json"
    previous = path.read_bytes()

    class RejectingValidator(KnowledgeGraphValidator):
        def require_valid(self, graph: KnowledgeGraph, project_index: ProjectIndex) -> None:
            raise KnowledgeGraphValidationError("rejected")

    service.validator = RejectingValidator()
    with pytest.raises(KnowledgeGraphValidationError):
        service.build(repository)
    assert path.read_bytes() == previous

    limited = graph_service(tmp_path, max_nodes=1)
    with pytest.raises(KnowledgeGraphLimitExceededError):
        limited.build(repository)
    assert path.read_bytes() == previous


@pytest.mark.parametrize(
    "content",
    ["invalid", '{"schema_version":"9.0","repositories":{}}'],
)
def test_corrupt_graph_store_is_explicit(tmp_path: Path, content: str) -> None:
    path = tmp_path / "memory" / "knowledge_graph.json"
    path.parent.mkdir()
    path.write_text(content, encoding="utf-8")

    with pytest.raises(KnowledgeGraphCorruptionError):
        graph_service(tmp_path).graph_store.load()


def test_input_workspace_mismatch_is_rejected(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    write(repository / "app.py")
    prepare_inputs(tmp_path, repository, "workspace-id")
    service = graph_service(tmp_path)
    project_index = service.index_store.get("workspace-id")
    assert project_index is not None
    service.index_store.save(
        "workspace-id",
        project_index.model_copy(
            update={
                "generation": project_index.generation.model_copy(update={"workspace_id": "wrong"})
            }
        ),
    )

    with pytest.raises(KnowledgeGraphInputMismatchError, match="workspace"):
        service.build(repository, "workspace-id", "ERP")
