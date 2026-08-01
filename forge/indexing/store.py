"""Atomic, validated project-index persistence."""

import json
import os
from pathlib import Path

from pydantic import ValidationError

from forge.indexing.errors import IndexCorruptionError, IndexPersistenceError
from forge.indexing.models import IndexStore, ProjectIndex


class ProjectIndexStore:
    """Persist independent repository indexes without silent recovery."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> IndexStore:
        """Load and validate the complete store, or return an empty store when absent."""
        if not self.path.exists():
            return IndexStore()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return IndexStore.model_validate(data)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise IndexCorruptionError(f"Index store is corrupt or incompatible: {exc}") from exc

    def get(self, repository_identity: str) -> ProjectIndex | None:
        """Return the latest successful index for one repository."""
        return self.load().repositories.get(repository_identity)

    def save(self, repository_identity: str, project_index: ProjectIndex) -> None:
        """Atomically replace one repository entry after validating the full store."""
        store = self.load()
        repositories = dict(store.repositories)
        repositories[repository_identity] = project_index
        updated = IndexStore(repositories=repositories)
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
            raise IndexPersistenceError(f"Unable to persist project index: {exc}") from exc
