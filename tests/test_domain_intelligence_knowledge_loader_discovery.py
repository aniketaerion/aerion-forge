from pathlib import Path

from forge.domain_intelligence.knowledge_loader.discovery import (
    discover_knowledge_sources,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
)


def test_knowledge_source_discovery(tmp_path: Path) -> None:
    (tmp_path / "guide.md").write_text(
        "# Engineering Guide",
        encoding="utf-8",
    )
    (tmp_path / "config.json").write_text(
        '{"version": 1}',
        encoding="utf-8",
    )
    (tmp_path / "firmware.bin").write_bytes(b"\x00\x01")

    sources = discover_knowledge_sources(
        tmp_path,
        KnowledgeLoaderPolicy(),
        max_files=100,
    )

    assert len(sources) == 2
    assert {source.kind for source in sources} == {
        KnowledgeSourceKind.MARKDOWN,
        KnowledgeSourceKind.JSON,
    }