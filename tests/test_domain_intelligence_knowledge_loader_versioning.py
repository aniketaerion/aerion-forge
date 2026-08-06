from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeSource,
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.versioning import (
    changed_source_paths,
)


def source(path: str, content_hash: str) -> KnowledgeSource:
    return KnowledgeSource(
        source_id=f"source-{path}-{content_hash}",
        path=path,
        kind=KnowledgeSourceKind.TEXT,
        size_bytes=10,
        content_hash=content_hash,
    )


def test_changed_source_paths() -> None:
    previous = (
        source("a.txt", "one"),
        source("b.txt", "same"),
    )
    current = (
        source("a.txt", "two"),
        source("b.txt", "same"),
        source("c.txt", "new"),
    )

    assert changed_source_paths(previous, current) == (
        "a.txt",
        "c.txt",
    )