"""Knowledge document loading for M4.7 Package 1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from forge.domain_intelligence.knowledge_loader.errors import (
    KnowledgeSourceError,
)
from forge.domain_intelligence.knowledge_loader.identifiers import (
    knowledge_document_identifier,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceKind,
)


def _title_from_text(path: Path, text: str) -> str:
    for line in text.splitlines():
        candidate = line.strip()
        if candidate.startswith("#"):
            title = candidate.lstrip("#").strip()
            if title:
                return title
    return path.stem.replace("_", " ").replace("-", " ").strip()


def _normalized_structured_text(
    value: Any,
) -> str:
    return json.dumps(
        value,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )


def load_knowledge_document(
    project_root: Path,
    source: KnowledgeSource,
) -> KnowledgeDocument:
    """Load and normalize one discovered knowledge source."""
    path = project_root / source.path

    try:
        raw = path.read_text(encoding=source.encoding)
    except (OSError, UnicodeDecodeError) as exc:
        raise KnowledgeSourceError(
            f"unable to read knowledge source: {source.path}"
        ) from exc

    try:
        if source.kind is KnowledgeSourceKind.JSON:
            text = _normalized_structured_text(json.loads(raw))
        elif source.kind is KnowledgeSourceKind.YAML:
            text = _normalized_structured_text(
                yaml.safe_load(raw)
            )
        else:
            text = raw.replace("\r\n", "\n").replace("\r", "\n")
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise KnowledgeSourceError(
            f"unable to parse knowledge source: {source.path}"
        ) from exc

    title = _title_from_text(path, text)
    payload = {
        "source_id": source.source_id,
        "title": title,
        "content_hash": source.content_hash,
    }

    return KnowledgeDocument(
        document_id=knowledge_document_identifier(payload),
        source_id=source.source_id,
        title=title,
        text=text,
        metadata={
            "path": source.path,
            "kind": source.kind.value,
            "content_hash": source.content_hash,
        },
    )


def load_knowledge_documents(
    project_root: Path,
    sources: tuple[KnowledgeSource, ...],
) -> tuple[KnowledgeDocument, ...]:
    """Load discovered sources into deterministic documents."""
    return tuple(
        load_knowledge_document(project_root, source)
        for source in sources
    )