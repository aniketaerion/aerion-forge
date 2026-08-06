from pathlib import Path

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadRequest,
)
from forge.domain_intelligence.knowledge_loader.service import (
    KnowledgeLoaderService,
)


def test_knowledge_loader_service(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "# Forge Guide\nKnowledge loading.",
        encoding="utf-8",
    )

    report = KnowledgeLoaderService().load(
        KnowledgeLoadRequest(
            repository_root=str(tmp_path),
            project_root="docs",
            chunk_size=128,
        )
    )

    assert report.manifest.project_root == "docs"
    assert len(report.sources) == 1
    assert len(report.documents) == 1
    assert len(report.chunks) >= 1
    assert report.manifest.chunk_ids == tuple(
        chunk.chunk_id for chunk in report.chunks
    )