"""Engineering Memory identifier and policy tests."""

import pytest

from forge.engineering_memory.errors import (
    EngineeringMemoryValidationError,
)
from forge.engineering_memory.identifiers import (
    build_evidence_id,
    build_generation_id,
    build_memory_fingerprint,
    build_memory_id,
    build_relationship_id,
    build_store_fingerprint,
    canonical_hash,
    normalize_memory_title,
    validate_evidence_id,
    validate_fingerprint,
    validate_generation_id,
    validate_memory_id,
    validate_relationship_id,
)
from forge.engineering_memory.models import (
    MemoryConfidence,
    MemoryEvidence,
    MemoryEvidenceType,
    MemoryRecord,
    MemoryRelationshipType,
    MemoryRetentionPolicy,
    MemoryType,
)
from forge.engineering_memory.policies import (
    confidence_is_allowed,
    normalize_tag,
    normalize_tags,
    requires_permanent_retention,
    requires_verified_evidence,
    retention_policy_is_allowed,
    validate_memory_policy,
)

FP_A = "a" * 64
MEMORY_A = "memory-" + ("a" * 20)
MEMORY_B = "memory-" + ("b" * 20)


def _record() -> MemoryRecord:
    evidence = MemoryEvidence(
        evidence_id=build_evidence_id(
            evidence_type=MemoryEvidenceType.MISSION_PLAN,
            reference="memory/missions.json",
            fingerprint=FP_A,
        ),
        evidence_type=MemoryEvidenceType.MISSION_PLAN,
        reference="memory/missions.json",
        fingerprint=FP_A,
        description="Mission evidence.",
    )

    draft = MemoryRecord(
        memory_id=build_memory_id(
            memory_type=MemoryType.MISSION,
            title="Mission Memory",
            source_fingerprints={"mission": FP_A},
        ),
        memory_fingerprint="0" * 64,
        memory_type=MemoryType.MISSION,
        title="Mission Memory",
        summary="Mission summary.",
        rationale="Persisted mission evidence.",
        mission_ids=("mission-1",),
        evidence=(evidence,),
        confidence=MemoryConfidence.VERIFIED,
        retention_policy=MemoryRetentionPolicy.PROJECT_LIFETIME,
        created_from_fingerprints={"mission": FP_A},
    )

    return draft.model_copy(update={"memory_fingerprint": build_memory_fingerprint(draft)})


def test_canonical_hash_is_order_independent() -> None:
    assert canonical_hash({"b": 2, "a": 1}) == canonical_hash({"a": 1, "b": 2})


def test_title_normalization_is_stable() -> None:
    assert normalize_memory_title("  Mission   MEMORY ") == "mission memory"


def test_blank_title_is_rejected() -> None:
    with pytest.raises(EngineeringMemoryValidationError):
        normalize_memory_title("   ")


def test_memory_id_is_deterministic() -> None:
    first = build_memory_id(
        memory_type=MemoryType.MISSION,
        title="Mission Memory",
        source_fingerprints={"mission": FP_A},
    )
    second = build_memory_id(
        memory_type=MemoryType.MISSION,
        title=" mission   memory ",
        source_fingerprints={"mission": FP_A},
    )

    assert first == second
    assert validate_memory_id(first)


def test_memory_id_requires_fingerprints() -> None:
    with pytest.raises(EngineeringMemoryValidationError):
        build_memory_id(
            memory_type=MemoryType.MISSION,
            title="Mission Memory",
            source_fingerprints={},
        )


def test_evidence_id_is_valid() -> None:
    evidence_id = build_evidence_id(
        evidence_type=MemoryEvidenceType.MISSION_PLAN,
        reference="memory/missions.json",
        fingerprint=FP_A,
    )

    assert validate_evidence_id(evidence_id)


def test_relationship_id_is_valid() -> None:
    relationship_id = build_relationship_id(
        relationship_type=MemoryRelationshipType.DERIVED_FROM,
        source_memory_id=MEMORY_A,
        target_memory_id=MEMORY_B,
        rationale="Derived from prior memory.",
    )

    assert validate_relationship_id(relationship_id)


def test_relationship_id_rejects_self_reference() -> None:
    with pytest.raises(EngineeringMemoryValidationError):
        build_relationship_id(
            relationship_type=(MemoryRelationshipType.REFERENCES),
            source_memory_id=MEMORY_A,
            target_memory_id=MEMORY_A,
            rationale="Invalid self reference.",
        )


def test_memory_fingerprint_is_deterministic() -> None:
    record = _record()

    assert build_memory_fingerprint(record) == build_memory_fingerprint(record)
    assert validate_fingerprint(record.memory_fingerprint)


def test_store_fingerprint_is_order_independent() -> None:
    record = _record()

    first = build_store_fingerprint({record.memory_id: record})
    second = build_store_fingerprint(dict(reversed([(record.memory_id, record)])))

    assert first == second


def test_generation_id_is_valid() -> None:
    generation_id = build_generation_id(store_fingerprint=FP_A)

    assert validate_generation_id(generation_id)


def test_tag_normalization() -> None:
    assert normalize_tag("  Release Evidence  ") == ("release-evidence")


def test_tags_are_deduplicated_and_sorted() -> None:
    assert normalize_tags((" Beta ", "alpha", "beta")) == ("alpha", "beta")


def test_decisions_require_permanent_retention() -> None:
    assert requires_permanent_retention(MemoryType.DECISION)
    assert not retention_policy_is_allowed(
        MemoryType.DECISION,
        MemoryRetentionPolicy.PROJECT_LIFETIME,
    )


def test_decisions_require_verified_evidence() -> None:
    assert requires_verified_evidence(MemoryType.DECISION)
    assert not confidence_is_allowed(
        MemoryType.DECISION,
        MemoryConfidence.HIGH,
        allow_unknown=False,
    )


def test_unknown_confidence_policy() -> None:
    assert not confidence_is_allowed(
        MemoryType.MISSION,
        MemoryConfidence.UNKNOWN,
        allow_unknown=False,
    )
    assert confidence_is_allowed(
        MemoryType.MISSION,
        MemoryConfidence.UNKNOWN,
        allow_unknown=True,
    )


def test_invalid_policy_raises() -> None:
    with pytest.raises(EngineeringMemoryValidationError):
        validate_memory_policy(
            memory_type=MemoryType.DECISION,
            confidence=MemoryConfidence.HIGH,
            retention_policy=(MemoryRetentionPolicy.PROJECT_LIFETIME),
            allow_unknown_confidence=False,
            allow_temporary_records=True,
        )
