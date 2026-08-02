"""Engineering Memory aggregate validator tests."""

import pytest

from forge.engineering_memory.errors import (
    EngineeringMemoryValidationError,
)
from forge.engineering_memory.identifiers import (
    build_evidence_id,
    build_generation_id,
    build_memory_fingerprint,
    build_memory_id,
    build_store_fingerprint,
)
from forge.engineering_memory.models import (
    EngineeringMemoryConfiguration,
    EngineeringMemoryGeneration,
    EngineeringMemoryStore,
    MemoryConfidence,
    MemoryEvidence,
    MemoryEvidenceType,
    MemoryRecord,
    MemoryRelationship,
    MemoryRelationshipType,
    MemoryRetentionPolicy,
    MemoryType,
)
from forge.engineering_memory.validator import (
    EngineeringMemoryValidator,
)

FP_A = "a" * 64


def _record(
    *,
    memory_type: MemoryType = MemoryType.MISSION,
    confidence: MemoryConfidence = MemoryConfidence.VERIFIED,
    retention: MemoryRetentionPolicy = (MemoryRetentionPolicy.PROJECT_LIFETIME),
) -> MemoryRecord:
    memory_id = build_memory_id(
        memory_type=memory_type,
        title="Engineering memory",
        source_fingerprints={"source": FP_A},
    )
    evidence = MemoryEvidence(
        evidence_id=build_evidence_id(
            evidence_type=MemoryEvidenceType.MISSION_PLAN,
            reference="memory/missions.json",
            fingerprint=FP_A,
        ),
        evidence_type=MemoryEvidenceType.MISSION_PLAN,
        reference="memory/missions.json",
        fingerprint=FP_A,
        description="Verified evidence.",
    )
    draft = MemoryRecord(
        memory_id=memory_id,
        memory_fingerprint="0" * 64,
        memory_type=memory_type,
        title="Engineering memory",
        summary="Verified engineering memory.",
        rationale="Built from persisted evidence.",
        mission_ids=("mission-1",),
        evidence=(evidence,),
        confidence=confidence,
        retention_policy=retention,
        created_from_fingerprints={"source": FP_A},
    )

    return draft.model_copy(update={"memory_fingerprint": build_memory_fingerprint(draft)})


def _store(
    record: MemoryRecord,
) -> EngineeringMemoryStore:
    records = {record.memory_id: record}
    fingerprint = build_store_fingerprint(records)
    generation = EngineeringMemoryGeneration(
        generation_id=build_generation_id(store_fingerprint=fingerprint),
        store_fingerprint=fingerprint,
        record_count=1,
        relationship_count=len(record.relationships),
        evidence_count=len(record.evidence),
    )

    return EngineeringMemoryStore(
        records=records,
        generation=generation,
    )


def test_valid_record_passes() -> None:
    result = EngineeringMemoryValidator().validate_record(_record())

    assert result.valid
    assert result.messages == ()


def test_invalid_memory_id_fails() -> None:
    record = _record().model_copy(update={"memory_id": "invalid"})

    result = EngineeringMemoryValidator().validate_record(record)

    assert not result.valid
    assert any(message.field == "memory_id" for message in result.messages)


def test_invalid_record_fingerprint_fails() -> None:
    record = _record().model_copy(update={"memory_fingerprint": "a" * 64})

    result = EngineeringMemoryValidator().validate_record(record)

    assert not result.valid


def test_invalid_evidence_id_fails() -> None:
    record = _record()
    evidence = record.evidence[0].model_copy(update={"evidence_id": "invalid"})
    record = record.model_copy(update={"evidence": (evidence,)})

    result = EngineeringMemoryValidator().validate_record(record)

    assert not result.valid


def test_invalid_evidence_fingerprint_fails() -> None:
    record = _record()
    evidence = record.evidence[0].model_copy(update={"fingerprint": "invalid"})
    record = record.model_copy(update={"evidence": (evidence,)})

    result = EngineeringMemoryValidator().validate_record(record)

    assert not result.valid


def test_evidence_limit_is_enforced() -> None:
    configuration = EngineeringMemoryConfiguration(max_evidence_per_record=1)
    record = _record()
    second = record.evidence[0].model_copy(update={"evidence_id": "evidence-" + ("b" * 20)})
    record = record.model_copy(update={"evidence": (record.evidence[0], second)})

    result = EngineeringMemoryValidator(configuration).validate_record(record)

    assert not result.valid


def test_policy_violation_is_reported() -> None:
    record = _record(
        memory_type=MemoryType.DECISION,
        confidence=MemoryConfidence.HIGH,
        retention=MemoryRetentionPolicy.PROJECT_LIFETIME,
    )

    result = EngineeringMemoryValidator().validate_record(record)

    assert not result.valid
    assert any(message.field == "policy" for message in result.messages)


def test_valid_store_passes() -> None:
    result = EngineeringMemoryValidator().validate_store(_store(_record()))

    assert result.valid


def test_store_key_mismatch_fails() -> None:
    record = _record()
    store = EngineeringMemoryStore(records={"wrong-key": record})

    result = EngineeringMemoryValidator().validate_store(store)

    assert not result.valid


def test_missing_relationship_target_fails() -> None:
    record = _record()
    relationship = MemoryRelationship(
        relationship_id=("memory-relationship-" + ("a" * 20)),
        relationship_type=MemoryRelationshipType.REFERENCES,
        source_memory_id=record.memory_id,
        target_memory_id="memory-" + ("b" * 20),
        rationale="References missing memory.",
    )
    record = record.model_copy(update={"relationships": (relationship,)})
    record = record.model_copy(update={"memory_fingerprint": build_memory_fingerprint(record)})

    result = EngineeringMemoryValidator().validate_store(
        EngineeringMemoryStore(records={record.memory_id: record})
    )

    assert not result.valid


def test_generation_fingerprint_mismatch_fails() -> None:
    store = _store(_record())
    assert store.generation is not None

    generation = store.generation.model_copy(update={"store_fingerprint": "b" * 64})
    store = store.model_copy(update={"generation": generation})

    result = EngineeringMemoryValidator().validate_store(store)

    assert not result.valid


def test_generation_record_count_mismatch_fails() -> None:
    store = _store(_record())
    assert store.generation is not None

    generation = store.generation.model_copy(update={"record_count": 2})
    store = store.model_copy(update={"generation": generation})

    result = EngineeringMemoryValidator().validate_store(store)

    assert not result.valid


def test_validate_record_or_raise() -> None:
    invalid = _record().model_copy(update={"memory_id": "invalid"})

    with pytest.raises(EngineeringMemoryValidationError):
        EngineeringMemoryValidator().validate_record_or_raise(invalid)


def test_validate_store_or_raise() -> None:
    record = _record()
    invalid = EngineeringMemoryStore(records={"wrong": record})

    with pytest.raises(EngineeringMemoryValidationError):
        EngineeringMemoryValidator().validate_store_or_raise(invalid)
