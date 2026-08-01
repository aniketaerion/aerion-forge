import hashlib
from pathlib import Path

from tests.knowledge_helpers import graph_service, prepare_inputs, write


def report_hashes(path: Path) -> dict[str, str]:
    return {
        item.name: hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.glob("KNOWLEDGE_*"))
    }


def test_graph_ids_fingerprint_and_reports_are_deterministic(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    write(repository / "src" / "app.py")
    prepare_inputs(tmp_path, repository)
    service = graph_service(tmp_path)
    first = service.build(repository)
    second = service.build(repository)
    second_hashes = report_hashes(tmp_path / "reports")
    third = service.build(repository)

    assert (
        first.graph.generation.graph_state_fingerprint
        == second.graph.generation.graph_state_fingerprint
    )
    assert (
        second.graph.generation.graph_state_fingerprint
        == third.graph.generation.graph_state_fingerprint
    )
    assert [node.node_id for node in second.graph.nodes] == [
        node.node_id for node in third.graph.nodes
    ]
    assert [edge.edge_id for edge in second.graph.edges] == [
        edge.edge_id for edge in third.graph.edges
    ]
    assert second_hashes == report_hashes(tmp_path / "reports")
    assert second.changes.added_nodes == []
    assert second.changes.removed_nodes == []


def test_added_removed_and_renamed_files_change_path_derived_nodes(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    write(repository / "src" / "old.py", "same")
    prepare_inputs(tmp_path, repository)
    service = graph_service(tmp_path)
    first = service.build(repository)
    old_id = next(node.node_id for node in first.graph.nodes if node.path == "src/old.py")
    (repository / "src" / "old.py").rename(repository / "src" / "new.py")
    prepare_inputs(tmp_path, repository)

    changed = service.build(repository)
    new_id = next(node.node_id for node in changed.graph.nodes if node.path == "src/new.py")

    assert old_id != new_id
    assert old_id in {change.entity_id for change in changed.changes.removed_nodes}
    assert new_id in {change.entity_id for change in changed.changes.added_nodes}
    assert changed.graph.generation.previous_generation_id == first.graph.generation.generation_id


def test_new_application_and_dependency_update_graph(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    write(repository / "README.md")
    prepare_inputs(tmp_path, repository)
    service = graph_service(tmp_path)
    service.build(repository)
    write(repository / "apps" / "web" / "package.json", '{"dependencies":{"react":"19"}}')
    write(repository / "apps" / "web" / "App.tsx")
    prepare_inputs(tmp_path, repository)

    result = service.build(repository)

    assert any(
        node.node_type.value == "application" and node.path == "apps/web"
        for node in result.graph.nodes
    )
    assert any(node.node_type.value == "dependency" for node in result.graph.nodes)
    assert result.changes.added_nodes
