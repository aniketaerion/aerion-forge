"""Engineering Memory model contract tests."""

import pytest
from pydantic import ValidationError

from forge.engineering_memory.models import (
    SCHEMA_VERSION,
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

FP_A = "a" * 64
FP_B = "b" * 64
MEMORY_A = "memory-" + ("a" * 20)
MEMORY_B = "memory-" + ("b" * 20)


def _evidence(
    evidence_id: str = "evidence-" + ("a" * 20),
) -> MemoryEvidence:
    return MemoryEvidence(
        evidence_id=evidence_id,
        evidence_type=MemoryEvidenceType.MISSION_PLAN,
        reference="memory/missions.json",
        fingerprint=FP_A,
        description="Persisted mission evidence.",
    )


def _record(
    *,
    memory_id: str = MEMORY_A,
    memory_fingerprint: str = FP_B,
    evidence: tuple[MemoryEvidence, ...] | None = None,
    relationships: tuple[MemoryRelationship, ...] = (),
    mission_ids: tuple[str, ...] = ("mission-1",),
    memory_type: MemoryType = MemoryType.MISSION,
    confidence: MemoryConfidence = MemoryConfidence.VERIFIED,
    retention_policy: MemoryRetentionPolicy = (MemoryRetentionPolicy.PROJECT_LIFETIME),
) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        memory_fingerprint=memory_fingerprint,
        memory_type=memory_type,
        title="Mission engineering memory",
        summary="Verified mission summary.",
        rationale="Derived from persisted Forge artifacts.",
        mission_ids=mission_ids,
        evidence=((_evidence(),) if evidence is None else evidence),
        relationships=relationships,
        confidence=confidence,
        retention_policy=retention_policy,
        created_from_fingerprints={"mission": FP_A},
    )


def test_schema_version_is_frozen() -> None:
    assert SCHEMA_VERSION == "1.0"


def test_configuration_defaults_are_safe() -> None:
    configuration = EngineeringMemoryConfiguration()

    assert configuration.enabled
    assert configuration.strict
    assert not configuration.allow_unknown_confidence
    assert configuration.max_records == 10000


def test_models_are_immutable() -> None:
    record = _record()

    with pytest.raises(ValidationError):
        record.title = "Changed"


def test_unknown_fields_are_rejected() -> None:
    payload = _record().model_dump()
    payload["unknown"] = True

    with pytest.raises(ValidationError):
        MemoryRecord.model_validate(payload)


@pytest.mark.parametrize(
    "field",
    [
        "memory_id",
        "memory_fingerprint",
        "title",
        "summary",
        "rationale",
    ],
)
def test_blank_record_fields_are_rejected(field: str) -> None:
    payload = _record().model_dump()
    payload[field] = "   "

    with pytest.raises(ValidationError):
        MemoryRecord.model_validate(payload)


def test_evidence_is_required() -> None:
    with pytest.raises(ValidationError):
        _record(evidence=())


def test_lineage_is_required() -> None:
    payload = _record().model_dump()
    payload["mission_ids"] = ()
    payload["task_ids"] = ()
    payload["assessment_ids"] = ()
    payload["capability_ids"] = ()
    payload["milestones"] = ()
    payload["source_artifacts"] = ()

    with pytest.raises(ValidationError):
        MemoryRecord.model_validate(payload)


def test_string_collections_are_normalized() -> None:
    payload = _record().model_dump()
    payload["mission_ids"] = (
        " mission-b ",
        "mission-a",
        "mission-b",
    )
    payload["tags"] = (" beta ", "alpha", "alpha")

    record = MemoryRecord.model_validate(payload)

    assert record.mission_ids == ("mission-a", "mission-b")
    assert record.tags == ("alpha", "beta")


def test_duplicate_evidence_ids_are_rejected() -> None:
    duplicate = _evidence()

    with pytest.raises(ValidationError):
        _record(evidence=(duplicate, duplicate))


def test_relationship_cannot_reference_itself() -> None:
    with pytest.raises(ValidationError):
        MemoryRelationship(
            relationship_id=("memory-relationship-" + ("a" * 20)),
            relationship_type=MemoryRelationshipType.REFERENCES,
            source_memory_id=MEMORY_A,
            target_memory_id=MEMORY_A,
            rationale="Self reference.",
        )


def test_relationship_must_originate_from_record() -> None:
    relationship = MemoryRelationship(
        relationship_id="memory-relationship-" + ("a" * 20),
        relationship_type=MemoryRelationshipType.REFERENCES,
        source_memory_id=MEMORY_B,
        target_memory_id=MEMORY_A,
        rationale="Invalid source.",
    )

    with pytest.raises(ValidationError):
        _record(relationships=(relationship,))


def test_duplicate_relationship_ids_are_rejected() -> None:
    relationship = MemoryRelationship(
        relationship_id="memory-relationship-" + ("a" * 20),
        relationship_type=MemoryRelationshipType.REFERENCES,
        source_memory_id=MEMORY_A,
        target_memory_id=MEMORY_B,
        rationale="References another record.",
    )

    with pytest.raises(ValidationError):
        _record(relationships=(relationship, relationship))


def test_store_defaults_are_empty() -> None:
    store = EngineeringMemoryStore()

    assert store.records == {}
    assert store.history == {}
    assert store.generation is None


def test_store_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        EngineeringMemoryStore.model_validate(
            {
                "records": {},
                "history": {},
                "unexpected": True,
            }
        )


def test_generation_rejects_blank_identity() -> None:
    with pytest.raises(ValidationError):
        EngineeringMemoryGeneration(
            generation_id=" ",
            store_fingerprint=FP_A,
            record_count=0,
            relationship_count=0,
            evidence_count=0,
        )


def test_serialization_is_deterministic() -> None:
    first = _record().model_dump_json()
    second = _record().model_dump_json()

    assert first == second


def test_round_trip_serialization() -> None:
    record = _record()

    restored = MemoryRecord.model_validate_json(record.model_dump_json())

    assert restored == record
