"""Atomic deterministic persistence for Engineering Memory."""

import json
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path

from pydantic import ValidationError

from forge.engineering_memory.errors import (
    EngineeringMemoryPersistenceError,
    EngineeringMemorySchemaMismatchError,
    EngineeringMemoryStoreCorruptionError,
)
from forge.engineering_memory.identifiers import (
    build_store_fingerprint,
)
from forge.engineering_memory.models import (
    SCHEMA_VERSION,
    EngineeringMemoryGeneration,
    EngineeringMemoryStore,
    MemoryRecord,
)
from forge.engineering_memory.validator import (
    EngineeringMemoryValidator,
)


class EngineeringMemoryRepository:
    """Persist Engineering Memory without partial replacement."""

    def __init__(
        self,
        path: Path,
        *,
        history_limit: int = 5,
        validator: EngineeringMemoryValidator | None = None,
    ) -> None:
        if history_limit < 0:
            raise ValueError("history_limit cannot be negative.")

        self.path = path
        self.history_limit = history_limit
        self.validator = validator if validator is not None else EngineeringMemoryValidator()

    def load(self) -> EngineeringMemoryStore:
        """Load and validate persisted Engineering Memory."""

        if not self.path.exists():
            return EngineeringMemoryStore()

        try:
            raw = self.path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as exc:
            raise EngineeringMemoryStoreCorruptionError(
                "Persisted Engineering Memory is unreadable."
            ) from exc

        if not isinstance(payload, dict):
            raise EngineeringMemoryStoreCorruptionError(
                "Persisted Engineering Memory must be a JSON object."
            )

        schema_version = payload.get("schema_version")

        if schema_version != SCHEMA_VERSION:
            raise EngineeringMemorySchemaMismatchError(
                f"Unsupported Engineering Memory schema: {schema_version!r}."
            )

        try:
            store = EngineeringMemoryStore.model_validate(payload)
        except ValidationError as exc:
            raise EngineeringMemoryStoreCorruptionError(
                "Persisted Engineering Memory violates the store contract."
            ) from exc

        try:
            self.validator.validate_store_or_raise(store)
        except Exception as exc:
            raise EngineeringMemoryStoreCorruptionError(
                "Persisted Engineering Memory failed aggregate validation."
            ) from exc

        return store

    def save(
        self,
        records: Iterable[MemoryRecord],
        generation: EngineeringMemoryGeneration,
    ) -> EngineeringMemoryStore:
        """Atomically merge and persist memory records."""

        incoming = self._normalize_records(records)

        if not incoming:
            raise EngineeringMemoryPersistenceError(
                "At least one Engineering Memory record is required for persistence."
            )

        previous = self.load()

        active = dict(previous.records)
        history = {memory_id: list(versions) for memory_id, versions in previous.history.items()}

        for memory_id, record in incoming.items():
            existing = active.get(memory_id)

            if existing is not None and existing.memory_fingerprint != record.memory_fingerprint:
                versions = history.setdefault(memory_id, [])
                versions.append(existing)

                if self.history_limit == 0:
                    history.pop(memory_id, None)
                else:
                    history[memory_id] = versions[-self.history_limit :]

            active[memory_id] = record

        active = {memory_id: active[memory_id] for memory_id in sorted(active)}

        self._validate_generation(
            records=active,
            generation=generation,
        )

        updated = EngineeringMemoryStore(
            records=active,
            history={
                memory_id: history[memory_id] for memory_id in sorted(history) if history[memory_id]
            },
            generation=generation,
        )

        self.validator.validate_store_or_raise(updated)
        self._write_and_verify(updated)

        return self.load()

    def replace_all(
        self,
        records: Iterable[MemoryRecord],
        generation: EngineeringMemoryGeneration,
    ) -> EngineeringMemoryStore:
        """Replace the active record set transactionally."""

        incoming = self._normalize_records(records)

        self._validate_generation(
            records=incoming,
            generation=generation,
        )

        previous = self.load()
        history = {memory_id: list(versions) for memory_id, versions in previous.history.items()}

        for memory_id, existing in previous.records.items():
            replacement = incoming.get(memory_id)

            if replacement is None or replacement.memory_fingerprint != existing.memory_fingerprint:
                versions = history.setdefault(memory_id, [])
                versions.append(existing)

                if self.history_limit == 0:
                    history.pop(memory_id, None)
                else:
                    history[memory_id] = versions[-self.history_limit :]

        updated = EngineeringMemoryStore(
            records={memory_id: incoming[memory_id] for memory_id in sorted(incoming)},
            history={
                memory_id: history[memory_id] for memory_id in sorted(history) if history[memory_id]
            },
            generation=generation,
        )

        self.validator.validate_store_or_raise(updated)
        self._write_and_verify(updated)

        return self.load()

    def delete(
        self,
        memory_id: str,
    ) -> EngineeringMemoryStore:
        """Delete one active record and retain bounded history."""

        normalized_id = memory_id.strip()

        if not normalized_id:
            raise EngineeringMemoryPersistenceError("memory_id cannot be blank.")

        previous = self.load()

        if normalized_id not in previous.records:
            return previous

        active = dict(previous.records)
        history = {key: list(versions) for key, versions in previous.history.items()}

        removed = active.pop(normalized_id)

        if self.history_limit > 0:
            versions = history.setdefault(normalized_id, [])
            versions.append(removed)
            history[normalized_id] = versions[-self.history_limit :]
        else:
            history.pop(normalized_id, None)

        generation = self._generation_for_records(
            records=active,
            previous_generation=previous.generation,
        )

        updated = EngineeringMemoryStore(
            records={key: active[key] for key in sorted(active)},
            history={key: history[key] for key in sorted(history) if history[key]},
            generation=generation,
        )

        self.validator.validate_store_or_raise(updated)
        self._write_and_verify(updated)

        return self.load()

    def snapshot_bytes(self) -> bytes | None:
        """Return current store bytes for rollback."""

        if not self.path.exists():
            return None

        try:
            return self.path.read_bytes()
        except OSError as exc:
            raise EngineeringMemoryPersistenceError(
                "Unable to snapshot Engineering Memory."
            ) from exc

    def restore_bytes(
        self,
        snapshot: bytes | None,
    ) -> None:
        """Restore a previous store snapshot."""

        if snapshot is None:
            try:
                self.path.unlink(missing_ok=True)
            except OSError as exc:
                raise EngineeringMemoryPersistenceError(
                    "Unable to remove Engineering Memory during rollback."
                ) from exc

            return

        self._atomic_write(snapshot)

    def probe_write(self) -> None:
        """Verify that same-directory atomic writes are supported."""

        directory = self.path.parent
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary: Path | None = None

        try:
            descriptor, name = tempfile.mkstemp(
                prefix=".engineering-memory-probe-",
                suffix=".tmp",
                dir=directory,
            )
            temporary = Path(name)

            with os.fdopen(descriptor, "wb") as stream:
                stream.write(b'{"probe":"engineering-memory"}\n')
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise EngineeringMemoryPersistenceError(
                "Engineering Memory write probe failed."
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _normalize_records(
        self,
        records: Iterable[MemoryRecord],
    ) -> dict[str, MemoryRecord]:
        normalized: dict[str, MemoryRecord] = {}

        for record in records:
            self.validator.validate_record_or_raise(record)

            if record.memory_id in normalized:
                raise EngineeringMemoryPersistenceError(
                    f"Duplicate memory ID in persistence request: {record.memory_id}"
                )

            normalized[record.memory_id] = record

        return {memory_id: normalized[memory_id] for memory_id in sorted(normalized)}

    def _validate_generation(
        self,
        *,
        records: dict[str, MemoryRecord],
        generation: EngineeringMemoryGeneration,
    ) -> None:
        expected_fingerprint = build_store_fingerprint(records)

        if generation.store_fingerprint != expected_fingerprint:
            raise EngineeringMemoryPersistenceError(
                "Generation store fingerprint does not match active records."
            )

        relationship_count = sum(len(record.relationships) for record in records.values())
        evidence_count = sum(len(record.evidence) for record in records.values())

        if generation.record_count != len(records):
            raise EngineeringMemoryPersistenceError(
                "Generation record count does not match active records."
            )

        if generation.relationship_count != relationship_count:
            raise EngineeringMemoryPersistenceError(
                "Generation relationship count does not match active records."
            )

        if generation.evidence_count != evidence_count:
            raise EngineeringMemoryPersistenceError(
                "Generation evidence count does not match active records."
            )

    def _generation_for_records(
        self,
        *,
        records: dict[str, MemoryRecord],
        previous_generation: (EngineeringMemoryGeneration | None),
    ) -> EngineeringMemoryGeneration | None:
        if not records:
            return None

        from forge.engineering_memory.identifiers import (
            build_generation_id,
        )

        store_fingerprint = build_store_fingerprint(records)
        previous_id = previous_generation.generation_id if previous_generation is not None else None

        return EngineeringMemoryGeneration(
            generation_id=build_generation_id(
                store_fingerprint=store_fingerprint,
                previous_generation_id=previous_id,
            ),
            previous_generation_id=previous_id,
            store_fingerprint=store_fingerprint,
            record_count=len(records),
            relationship_count=sum(len(record.relationships) for record in records.values()),
            evidence_count=sum(len(record.evidence) for record in records.values()),
        )

    def _write_and_verify(
        self,
        store: EngineeringMemoryStore,
    ) -> None:
        content = (
            store.model_dump_json(
                indent=2,
                exclude_none=False,
            )
            + "\n"
        ).encode("utf-8")

        snapshot = self.snapshot_bytes()

        try:
            self._atomic_write(content)
            reloaded = self.load()

            if reloaded != store:
                raise EngineeringMemoryPersistenceError(
                    "Engineering Memory failed post-write verification."
                )
        except Exception:
            self.restore_bytes(snapshot)
            raise

    def _atomic_write(
        self,
        content: bytes,
    ) -> None:
        """Write bytes using same-directory atomic replacement."""

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary: Path | None = None

        try:
            descriptor, name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            temporary = Path(name)

            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(
                temporary,
                self.path,
            )
            temporary = None
        except OSError as exc:
            raise EngineeringMemoryPersistenceError(
                "Atomic Engineering Memory replacement failed."
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
