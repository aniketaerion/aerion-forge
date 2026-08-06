from pathlib import Path

from forge.domain_intelligence.knowledge_loader.discovery import (
    discover_knowledge_sources,
)
from forge.domain_intelligence.knowledge_loader.loader import (
    load_knowledge_documents,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
)


def test_knowledge_document_loading(tmp_path: Path) -> None:
    (tmp_path / "guide.md").write_text(
        "# Flight Safety\nUse deterministic checks.",
        encoding="utf-8",
    )

    sources = discover_knowledge_sources(
        tmp_path,
        KnowledgeLoaderPolicy(),
        max_files=100,
    )
    documents = load_knowledge_documents(tmp_path, sources)

    assert len(documents) == 1
    assert documents[0].title == "Flight Safety"
    assert "deterministic checks" in documents[0].text