from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeChunk,
)
from forge.domain_intelligence.knowledge_loader.validation import (
    validate_chunks,
)


def test_validation_detects_chunk_ordinal_gap() -> None:
    chunks = (
        KnowledgeChunk(
            chunk_id="chunk-1",
            document_id="document-1",
            ordinal=0,
            text="First",
            token_estimate=1,
        ),
        KnowledgeChunk(
            chunk_id="chunk-2",
            document_id="document-1",
            ordinal=2,
            text="Third",
            token_estimate=1,
        ),
    )

    findings = validate_chunks(chunks)

    assert findings[0].category == "chunk-ordinal-gap"