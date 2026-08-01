"""Atomic safe configuration snapshot persistence."""

import json
import os
from pathlib import Path

from pydantic import ValidationError

from forge.configuration.errors import (
    ConfigurationPersistenceError,
    ConfigurationSchemaMismatchError,
    ConfigurationStoreCorruptionError,
)
from forge.configuration.models import SCHEMA_VERSION, ConfigurationSnapshot, ConfigurationStore


class ConfigurationRepository:
    def __init__(self, path: Path, history_limit: int = 5) -> None:
        self.path = path
        self.history_limit = history_limit

    def load(self) -> ConfigurationStore:
        if not self.path.exists():
            return ConfigurationStore()
        try:
            store = ConfigurationStore.model_validate_json(self.path.read_text(encoding="utf-8"))
        except (OSError, ValidationError) as exc:
            raise ConfigurationStoreCorruptionError(
                "Configuration store is corrupt or invalid."
            ) from exc
        if store.schema_version != SCHEMA_VERSION:
            raise ConfigurationSchemaMismatchError(
                f"Unsupported configuration schema: {store.schema_version}"
            )
        return store

    def save(self, snapshot: ConfigurationSnapshot) -> None:
        old = self.load()
        history = list(old.history)
        if (
            old.snapshot
            and old.snapshot.configuration_fingerprint != snapshot.configuration_fingerprint
        ):
            history.append(old.snapshot)
        history = history[-self.history_limit :] if self.history_limit else []
        content = (
            json.dumps(
                ConfigurationStore(snapshot=snapshot, history=history).model_dump(mode="json"),
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n"
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with temp.open("w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            temp.replace(self.path)
        except OSError as exc:
            temp.unlink(missing_ok=True)
            raise ConfigurationPersistenceError(
                "Unable to persist configuration snapshot."
            ) from exc
