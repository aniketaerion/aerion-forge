"""Knowledge-source discovery for M4.7 Package 1."""

from __future__ import annotations

import hashlib
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_source_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadStatus,
    KnowledgeSource,
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
    is_allowed_knowledge_path,
)

_KIND_BY_SUFFIX = {
    ".md": KnowledgeSourceKind.MARKDOWN,
    ".txt": KnowledgeSourceKind.TEXT,
    ".json": KnowledgeSourceKind.JSON,
    ".yaml": KnowledgeSourceKind.YAML,
    ".yml": KnowledgeSourceKind.YAML,
    ".toml": KnowledgeSourceKind.TOML,
    ".py": KnowledgeSourceKind.PYTHON,
}


def _content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def knowledge_source_kind(path: Path) -> KnowledgeSourceKind:
    return _KIND_BY_SUFFIX.get(
        path.suffix.lower(),
        KnowledgeSourceKind.UNKNOWN,
    )


def discover_knowledge_sources(
    project_root: Path,
    policy: KnowledgeLoaderPolicy,
    *,
    max_files: int,
) -> tuple[KnowledgeSource, ...]:
    """Discover deterministic, policy-approved knowledge files."""
    sources: list[KnowledgeSource] = []

    for path in sorted(project_root.rglob("*")):
        if len(sources) >= max_files:
            break

        if not is_allowed_knowledge_path(path, project_root, policy):
            continue

        relative = path.relative_to(project_root).as_posix()
        size_bytes = path.stat().st_size
        content_hash = _content_hash(path)
        payload = {
            "path": relative,
            "size_bytes": size_bytes,
            "content_hash": content_hash,
        }

        sources.append(
            KnowledgeSource(
                source_id=knowledge_source_identifier(payload),
                path=relative,
                kind=knowledge_source_kind(path),
                size_bytes=size_bytes,
                content_hash=content_hash,
                status=KnowledgeLoadStatus.DISCOVERED,
            )
        )

    return tuple(sources)