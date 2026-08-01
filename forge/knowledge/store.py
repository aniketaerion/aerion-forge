"""Atomic, schema-validated knowledge graph persistence."""

import json
import os
from pathlib import Path

from pydantic import ValidationError

from forge.knowledge.errors import (
    KnowledgeGraphCorruptionError,
    KnowledgeGraphPersistenceError,
)
from forge.knowledge.models import KnowledgeGraph, KnowledgeGraphStore


class KnowledgeGraphRepository:
    """Persist one latest valid graph per workspace or repository identity."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> KnowledgeGraphStore:
        if not self.path.exists():
            return KnowledgeGraphStore()
        try:
            return KnowledgeGraphStore.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            raise KnowledgeGraphCorruptionError(
                f"Knowledge graph store is corrupt or incompatible: {exc}"
            ) from exc

    def get(self, identity: str) -> KnowledgeGraph | None:
        return self.load().repositories.get(identity)

    def save(self, identity: str, graph: KnowledgeGraph) -> None:
        store = self.load()
        repositories = dict(store.repositories)
        repositories[identity] = graph
        updated = KnowledgeGraphStore(repositories=repositories)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                json.dump(
                    updated.model_dump(mode="json"),
                    stream,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise KnowledgeGraphPersistenceError(
                f"Unable to persist knowledge graph: {exc}"
            ) from exc
