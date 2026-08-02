"""Engineering Memory repository tests."""

import json
from pathlib import Path

import pytest

from forge.engineering_memory.builder import EngineeringMemoryBuilder
from forge.engineering_memory.errors import (
    EngineeringMemoryPersistenceError,
    EngineeringMemorySchemaMismatchError,
    EngineeringMemoryStoreCorruptionError,
)
from forge.engineering_memory.identifiers import (
    build_generation_id,
    build_memory_fingerprint,
    build_store_fingerprint,
)
from forge.engineering_memory.models import (
    EngineeringMemoryGeneration,
    MemoryRecord,
)
from forge.engineering_memory.store import (
    EngineeringMemoryRepository,
)
from tests.test_engineering_memory_builder import _inputs


def _records() -> tuple[MemoryRecord, ...]:
    mission, task_set, assessment = _inputs()

    return EngineeringMemoryBuilder().build(
        mission,
        task_set,
        assessment,
    )


def _generation(
    records: tuple[MemoryRecord, ...],
    *,
    previous_generation_id: str | None = None,
) -> EngineeringMemoryGeneration:
    active = {record.memory_id: record for record in records}
    store_fingerprint = build_store_fingerprint(active)

    return EngineeringMemoryGeneration(
        generation_id=build_generation_id(
            store_fingerprint=store_fingerprint,
            previous_generation_id=previous_generation_id,
        ),
        previous_generation_id=previous_generation_id,
        store_fingerprint=store_fingerprint,
        record_count=len(records),
        relationship_count=sum(len(record.relationships) for record in records),
        evidence_count=sum(len(record.evidence) for record in records),
    )


def test_load_returns_empty_store_when_file_is_missing(
    tmp_path: Path,
) -> None:
    repository = EngineeringMemoryRepository(tmp_path / "engineering-memory.json")

    store = repository.load()

    assert store.records == {}
    assert store.history == {}
    assert store.generation is None


def test_save_persists_records(
    tmp_path: Path,
) -> None:
    records = _records()
    repository = EngineeringMemoryRepository(tmp_path / "engineering-memory.json")

    store = repository.save(
        records,
        _generation(records),
    )

    assert len(store.records) == 3
    assert store.generation is not None


def test_save_round_trip_is_deterministic(
    tmp_path: Path,
) -> None:
    records = _records()
    repository = EngineeringMemoryRepository(tmp_path / "engineering-memory.json")

    first = repository.save(
        records,
        _generation(records),
    )
    second = repository.load()

    assert first == second


def test_store_json_is_valid_and_utf8(
    tmp_path: Path,
) -> None:
    records = _records()
    path = tmp_path / "engineering-memory.json"
    repository = EngineeringMemoryRepository(path)

    repository.save(
        records,
        _generation(records),
    )

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.0"
    assert len(payload["records"]) == 3


def test_save_rejects_empty_record_collection(
    tmp_path: Path,
) -> None:
    repository = EngineeringMemoryRepository(tmp_path / "engineering-memory.json")

    generation = EngineeringMemoryGeneration(
        generation_id=build_generation_id(store_fingerprint=build_store_fingerprint({})),
        store_fingerprint=build_store_fingerprint({}),
        record_count=0,
        relationship_count=0,
        evidence_count=0,
    )

    with pytest.raises(EngineeringMemoryPersistenceError):
        repository.save(
            (),
            generation,
        )


def test_save_rejects_duplicate_memory_ids(
    tmp_path: Path,
) -> None:
    records = _records()
    repository = EngineeringMemoryRepository(tmp_path / "engineering-memory.json")

    with pytest.raises(EngineeringMemoryPersistenceError):
        repository.save(
            (records[0], records[0]),
            _generation((records[0],)),
        )


def test_save_rejects_generation_fingerprint_mismatch(
    tmp_path: Path,
) -> None:
    records = _records()
    generation = _generation(records).model_copy(update={"store_fingerprint": "f" * 64})
    repository = EngineeringMemoryRepository(tmp_path / "engineering-memory.json")

    with pytest.raises(EngineeringMemoryPersistenceError):
        repository.save(
            records,
            generation,
        )


def test_changed_record_is_added_to_history(
    tmp_path: Path,
) -> None:
    records = _records()
    repository = EngineeringMemoryRepository(
        tmp_path / "engineering-memory.json",
        history_limit=5,
    )

    first_generation = _generation(records)
    first_store = repository.save(
        records,
        first_generation,
    )

    original = records[0]
    changed_draft = original.model_copy(
        update={
            "summary": original.summary + " Updated.",
            "memory_fingerprint": "0" * 64,
        }
    )
    changed = changed_draft.model_copy(
        update={"memory_fingerprint": (build_memory_fingerprint(changed_draft))}
    )

    updated_records = tuple(
        changed if record.memory_id == changed.memory_id else record for record in records
    )

    second_generation = _generation(
        updated_records,
        previous_generation_id=(
            first_store.generation.generation_id if first_store.generation is not None else None
        ),
    )

    updated = repository.save(
        updated_records,
        second_generation,
    )

    assert changed.memory_id in updated.history
    assert updated.history[changed.memory_id][-1] == original


def test_history_limit_is_enforced(
    tmp_path: Path,
) -> None:
    records = _records()
    repository = EngineeringMemoryRepository(
        tmp_path / "engineering-memory.json",
        history_limit=1,
    )

    current_records = records
    store = repository.save(
        current_records,
        _generation(current_records),
    )

    for suffix in (" First.", " Second."):
        original = current_records[0]
        draft = original.model_copy(
            update={
                "summary": original.summary + suffix,
                "memory_fingerprint": "0" * 64,
            }
        )
        changed = draft.model_copy(update={"memory_fingerprint": (build_memory_fingerprint(draft))})
        current_records = tuple(
            changed if record.memory_id == changed.memory_id else record
            for record in current_records
        )
        previous_id = store.generation.generation_id if store.generation is not None else None
        store = repository.save(
            current_records,
            _generation(
                current_records,
                previous_generation_id=previous_id,
            ),
        )

    assert len(store.history[current_records[0].memory_id]) == 1


def test_delete_removes_active_record(
    tmp_path: Path,
) -> None:
    records = _records()
    repository = EngineeringMemoryRepository(tmp_path / "engineering-memory.json")

    repository.save(
        records,
        _generation(records),
    )

    updated = repository.delete(records[0].memory_id)

    assert records[0].memory_id not in updated.records


def test_delete_unknown_record_is_noop(
    tmp_path: Path,
) -> None:
    records = _records()
    repository = EngineeringMemoryRepository(tmp_path / "engineering-memory.json")

    original = repository.save(
        records,
        _generation(records),
    )
    updated = repository.delete("memory-" + ("f" * 20))

    assert updated == original


def test_corrupt_json_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "engineering-memory.json"
    path.write_text(
        "{invalid-json",
        encoding="utf-8",
    )
    repository = EngineeringMemoryRepository(path)

    with pytest.raises(EngineeringMemoryStoreCorruptionError):
        repository.load()


def test_non_object_json_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "engineering-memory.json"
    path.write_text(
        "[]",
        encoding="utf-8",
    )
    repository = EngineeringMemoryRepository(path)

    with pytest.raises(EngineeringMemoryStoreCorruptionError):
        repository.load()


def test_unsupported_schema_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "engineering-memory.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "99.0",
                "records": {},
                "history": {},
                "generation": None,
            }
        ),
        encoding="utf-8",
    )
    repository = EngineeringMemoryRepository(path)

    with pytest.raises(EngineeringMemorySchemaMismatchError):
        repository.load()


def test_snapshot_and_restore(
    tmp_path: Path,
) -> None:
    records = _records()
    path = tmp_path / "engineering-memory.json"
    repository = EngineeringMemoryRepository(path)

    repository.save(
        records,
        _generation(records),
    )
    snapshot = repository.snapshot_bytes()

    path.write_text(
        "corrupted",
        encoding="utf-8",
    )
    repository.restore_bytes(snapshot)

    assert repository.load().records


def test_probe_write_does_not_create_store(
    tmp_path: Path,
) -> None:
    path = tmp_path / "engineering-memory.json"
    repository = EngineeringMemoryRepository(path)

    repository.probe_write()

    assert not path.exists()
