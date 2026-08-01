"""Atomic, schema-validated diagnostics persistence."""

import json
import os
from pathlib import Path

from pydantic import ValidationError

from forge.diagnostics.errors import (
    DiagnosticPersistenceError,
    DiagnosticSchemaMismatchError,
    DiagnosticStoreCorruptionError,
)
from forge.diagnostics.models import SCHEMA_VERSION, DiagnosticSnapshot, DiagnosticStore


class DiagnosticRepository:
    def __init__(self, path: Path, history_limit: int = 5) -> None:
        self.path = path
        self.history_limit = history_limit

    def load(self) -> DiagnosticStore:
        if not self.path.exists():
            return DiagnosticStore()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DiagnosticStoreCorruptionError("Diagnostic store is corrupt.") from exc
        if raw.get("schema_version") != SCHEMA_VERSION:
            raise DiagnosticSchemaMismatchError(
                f"Unsupported diagnostic schema: {raw.get('schema_version', 'missing')}"
            )
        try:
            return DiagnosticStore.model_validate(raw)
        except ValidationError as exc:
            raise DiagnosticStoreCorruptionError("Diagnostic store is invalid.") from exc

    def save(self, key: str, snapshot: DiagnosticSnapshot) -> None:
        previous = self.load()
        snapshots = dict(previous.snapshots)
        history = {name: list(values) for name, values in previous.history.items()}
        old = snapshots.get(key)
        if old and old.diagnostic_fingerprint != snapshot.diagnostic_fingerprint:
            history.setdefault(key, []).append(old)
        history[key] = history.get(key, [])[-self.history_limit :] if self.history_limit else []
        snapshots[key] = snapshot
        content = (
            json.dumps(
                DiagnosticStore(snapshots=snapshots, history=history).model_dump(mode="json"),
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
            raise DiagnosticPersistenceError("Unable to persist diagnostics.") from exc
