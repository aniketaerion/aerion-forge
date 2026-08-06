"""Knowledge-source versioning for M4.7 Package 2."""

from __future__ import annotations

from dataclasses import dataclass

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeSource,
)


@dataclass(frozen=True, slots=True)
class KnowledgeSourceVersion:
    source_id: str
    path: str
    content_hash: str


def source_version(
    source: KnowledgeSource,
) -> KnowledgeSourceVersion:
    return KnowledgeSourceVersion(
        source_id=source.source_id,
        path=source.path,
        content_hash=source.content_hash,
    )


def changed_source_paths(
    previous: tuple[KnowledgeSource, ...],
    current: tuple[KnowledgeSource, ...],
) -> tuple[str, ...]:
    previous_by_path = {
        source.path: source.content_hash
        for source in previous
    }
    current_by_path = {
        source.path: source.content_hash
        for source in current
    }

    paths = set(previous_by_path) | set(current_by_path)

    return tuple(
        sorted(
            path
            for path in paths
            if previous_by_path.get(path)
            != current_by_path.get(path)
        )
    )