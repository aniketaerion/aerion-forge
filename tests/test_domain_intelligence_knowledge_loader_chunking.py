from forge.domain_intelligence.knowledge_loader.chunking import (
    chunk_document,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
)


def test_document_chunking_is_deterministic() -> None:
    document = KnowledgeDocument(
        document_id="document-1",
        source_id="source-1",
        title="Guide",
        text="abcdefghij",
    )

    chunks = chunk_document(document, chunk_size=4)

    assert [chunk.text for chunk in chunks] == [
        "abcd",
        "efgh",
        "ij",
    ]
    assert [chunk.ordinal for chunk in chunks] == [0, 1, 2]