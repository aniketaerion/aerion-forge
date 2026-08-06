from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_chunk_identifier,
    knowledge_source_identifier,
)


def test_knowledge_source_identifier_is_deterministic() -> None:
    first = knowledge_source_identifier(
        {"path": "docs/guide.md", "hash": "abc"}
    )
    second = knowledge_source_identifier(
        {"hash": "abc", "path": "docs/guide.md"}
    )

    assert first == second
    assert first.startswith("knowledge-source-")


def test_knowledge_chunk_identifier_changes_by_ordinal() -> None:
    first = knowledge_chunk_identifier(
        {"document_id": "doc-1", "ordinal": 0}
    )
    second = knowledge_chunk_identifier(
        {"document_id": "doc-1", "ordinal": 1}
    )

    assert first != second