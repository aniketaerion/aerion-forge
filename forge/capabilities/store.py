"""Atomic, schema-validated capability registry persistence."""

import json
import os
from pathlib import Path

from pydantic import ValidationError

from forge.capabilities.errors import CapabilityPersistenceError, CapabilityStoreCorruptionError
from forge.capabilities.models import SCHEMA_VERSION, CapabilityRegistry, CapabilityRegistryStore


class CapabilityRegistryRepository:
    def __init__(self, path: Path, history_limit: int = 5) -> None:
        self.path = path
        self.history_limit = history_limit

    def load(self) -> CapabilityRegistryStore:
        if not self.path.exists():
            return CapabilityRegistryStore()
        try:
            store = CapabilityRegistryStore.model_validate_json(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, ValidationError) as exc:
            raise CapabilityStoreCorruptionError(
                f"Capability registry store is corrupt: {exc}"
            ) from exc
        if store.schema_version != SCHEMA_VERSION:
            raise CapabilityStoreCorruptionError(
                f"Unsupported capability registry schema: {store.schema_version}"
            )
        return store

    def save(self, registry: CapabilityRegistry) -> None:
        previous = self.load()
        history = list(previous.history)
        if (
            previous.registry
            and previous.registry.generation.registry_fingerprint
            != registry.generation.registry_fingerprint
        ):
            history.append(previous.registry)
        history = history[-self.history_limit :] if self.history_limit else []
        content = (
            json.dumps(
                CapabilityRegistryStore(registry=registry, history=history).model_dump(mode="json"),
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise CapabilityPersistenceError(
                f"Unable to persist capability registry: {exc}"
            ) from exc
