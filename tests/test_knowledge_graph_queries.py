from pathlib import Path

from forge.knowledge import KnowledgeGraphQuery, KnowledgeNodeType
from tests.knowledge_helpers import graph_service, prepare_inputs, write


def test_query_api_returns_typed_deterministic_results(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    write(repository / "apps" / "web" / "package.json", '{"dependencies":{"react":"19"}}')
    write(repository / "apps" / "web" / "src" / "App.tsx")
    prepare_inputs(tmp_path, repository)
    result = graph_service(tmp_path).build(repository)
    query = KnowledgeGraphQuery(result.graph, result.orphans)
    component = query.get_nodes_by_type(KnowledgeNodeType.APPLICATION)[0]
    manifest = query.get_manifests_for_component(component.node_id)[0]

    assert query.get_node(component.node_id) == component
    assert query.get_edges_from(component.node_id) == sorted(
        query.get_edges_from(component.node_id), key=lambda edge: edge.edge_id
    )
    assert query.get_edges_to(component.node_id)
    assert query.get_neighbors(component.node_id)
    assert query.get_files_for_component(component.node_id)
    file_node = query.get_files_for_component(component.node_id)[0]
    assert query.get_component_for_file(file_node.node_id) == component
    assert query.get_technologies_for_component(component.node_id)
    assert query.get_dependencies_for_manifest(manifest.node_id)
    assert query.get_orphans() == result.orphans
    assert query.get_node("missing") is None
