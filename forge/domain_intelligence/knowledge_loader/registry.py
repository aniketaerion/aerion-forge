"""Loader registry for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.loader import (
    load_knowledge_document,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeDocument,
    KnowledgeSource,
    KnowledgeSourceKind,
)

Loader = Callable[[Path, KnowledgeSource], KnowledgeDocument]


class KnowledgeLoaderRegistry:
    """Deterministic registry of source-kind loaders."""

    def __init__(self) -> None:
        self._loaders: dict[KnowledgeSourceKind, Loader] = {}

    @classmethod
    def default(cls) -> KnowledgeLoaderRegistry:
        registry = cls()

        for kind in (
            KnowledgeSourceKind.MARKDOWN,
            KnowledgeSourceKind.TEXT,
            KnowledgeSourceKind.JSON,
            KnowledgeSourceKind.YAML,
            KnowledgeSourceKind.TOML,
            KnowledgeSourceKind.PYTHON,
            KnowledgeSourceKind.DOCUMENTATION,
            KnowledgeSourceKind.MANIFEST,
            KnowledgeSourceKind.UNKNOWN,
        ):
            registry.register(kind, load_knowledge_document)

        return registry

    def register(
        self,
        kind: KnowledgeSourceKind,
        loader: Loader,
    ) -> None:
        self._loaders[kind] = loader

    def kinds(self) -> tuple[KnowledgeSourceKind, ...]:
        return tuple(
            sorted(
                self._loaders,
                key=lambda kind: kind.value,
            )
        )

    def load(
        self,
        project_root: Path,
        source: KnowledgeSource,
    ) -> KnowledgeDocument:
        loader = self._loaders.get(source.kind)
        if loader is None:
            loader = load_knowledge_document
        return loader(project_root, source)