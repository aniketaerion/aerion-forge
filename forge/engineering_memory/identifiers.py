"""Deterministic identifiers for Engineering Memory."""

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

from forge.engineering_memory.errors import (
    EngineeringMemoryValidationError,
)
from forge.engineering_memory.models import (
    EngineeringMemoryGeneration,
    MemoryEvidenceType,
    MemoryRecord,
    MemoryRelationshipType,
    MemoryType,
)

MEMORY_ID_PATTERN = re.compile(r"memory-[0-9a-f]{20}")
EVIDENCE_ID_PATTERN = re.compile(r"evidence-[0-9a-f]{20}")
RELATIONSHIP_ID_PATTERN = re.compile(r"memory-relationship-[0-9a-f]{20}")
GENERATION_ID_PATTERN = re.compile(r"memory-generation-[0-9a-f]{20}")
FINGERPRINT_PATTERN = re.compile(r"[0-9a-f]{64}")


def canonical_json(value: Any) -> str:
    """Serialize a value into canonical deterministic JSON."""

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    )


def canonical_hash(value: Any) -> str:
    """Return a deterministic SHA-256 hexadecimal hash."""

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _require_text(value: str, field: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise EngineeringMemoryValidationError(
            f"{field} cannot be blank during identifier generation."
        )

    return normalized


def normalize_memory_title(title: str) -> str:
    """Normalize a title for stable identity generation."""

    normalized = " ".join(title.strip().casefold().split())

    if not normalized:
        raise EngineeringMemoryValidationError("Memory title cannot be blank.")

    return normalized


def build_memory_id(
    *,
    memory_type: MemoryType,
    title: str,
    source_fingerprints: Mapping[str, str],
) -> str:
    """Build a stable Engineering Memory record identifier."""

    normalized_fingerprints = {
        key.strip(): value.strip()
        for key, value in source_fingerprints.items()
        if key.strip() and value.strip()
    }

    if not normalized_fingerprints:
        raise EngineeringMemoryValidationError("Memory identity requires source fingerprints.")

    payload = {
        "memory_type": memory_type.value,
        "title": normalize_memory_title(title),
        "source_fingerprints": dict(sorted(normalized_fingerprints.items())),
    }

    return f"memory-{canonical_hash(payload)[:20]}"


def build_evidence_id(
    *,
    evidence_type: MemoryEvidenceType,
    reference: str,
    fingerprint: str,
) -> str:
    """Build a stable evidence identifier."""

    payload = {
        "evidence_type": evidence_type.value,
        "reference": _require_text(
            reference,
            "reference",
        ),
        "fingerprint": _require_text(
            fingerprint,
            "fingerprint",
        ),
    }

    return f"evidence-{canonical_hash(payload)[:20]}"


def build_relationship_id(
    *,
    relationship_type: MemoryRelationshipType,
    source_memory_id: str,
    target_memory_id: str,
    rationale: str,
) -> str:
    """Build a stable directed relationship identifier."""

    source = _require_text(
        source_memory_id,
        "source_memory_id",
    )
    target = _require_text(
        target_memory_id,
        "target_memory_id",
    )

    if source == target:
        raise EngineeringMemoryValidationError("A memory relationship cannot reference itself.")

    payload = {
        "relationship_type": relationship_type.value,
        "source_memory_id": source,
        "target_memory_id": target,
        "rationale": " ".join(
            _require_text(
                rationale,
                "rationale",
            )
            .casefold()
            .split()
        ),
    }

    return f"memory-relationship-{canonical_hash(payload)[:20]}"


def memory_fingerprint_payload(
    record: MemoryRecord,
) -> dict[str, Any]:
    """Return canonical record content without its fingerprint."""

    payload = record.model_dump(mode="json")
    payload["memory_fingerprint"] = ""

    for field in (
        "mission_ids",
        "task_ids",
        "assessment_ids",
        "capability_ids",
        "milestones",
        "source_artifacts",
        "tags",
    ):
        payload[field] = sorted(payload[field])

    payload["evidence"] = sorted(
        payload["evidence"],
        key=lambda item: item["evidence_id"],
    )
    payload["relationships"] = sorted(
        payload["relationships"],
        key=lambda item: item["relationship_id"],
    )
    payload["created_from_fingerprints"] = dict(
        sorted(payload["created_from_fingerprints"].items())
    )

    return payload


def build_memory_fingerprint(
    record: MemoryRecord,
) -> str:
    """Build the deterministic memory-record fingerprint."""

    return canonical_hash(memory_fingerprint_payload(record))


def build_store_fingerprint(
    records: Mapping[str, MemoryRecord],
) -> str:
    """Build a deterministic fingerprint for the active store."""

    payload = {
        memory_id: memory_fingerprint_payload(record)
        for memory_id, record in sorted(records.items())
    }

    return canonical_hash(payload)


def build_generation_id(
    *,
    store_fingerprint: str,
    previous_generation_id: str | None = None,
) -> str:
    """Build deterministic Engineering Memory generation identity."""

    payload = {
        "store_fingerprint": _require_text(
            store_fingerprint,
            "store_fingerprint",
        ),
        "previous_generation_id": (
            previous_generation_id.strip() if previous_generation_id else None
        ),
    }

    return f"memory-generation-{canonical_hash(payload)[:20]}"


def generation_fingerprint_payload(
    generation: EngineeringMemoryGeneration,
) -> dict[str, Any]:
    """Return canonical generation metadata."""

    return generation.model_dump(mode="json")


def validate_memory_id(value: str) -> bool:
    """Return whether a memory ID matches the public contract."""

    return bool(MEMORY_ID_PATTERN.fullmatch(value))


def validate_evidence_id(value: str) -> bool:
    """Return whether an evidence ID matches the contract."""

    return bool(EVIDENCE_ID_PATTERN.fullmatch(value))


def validate_relationship_id(value: str) -> bool:
    """Return whether a relationship ID matches the contract."""

    return bool(RELATIONSHIP_ID_PATTERN.fullmatch(value))


def validate_generation_id(value: str) -> bool:
    """Return whether a generation ID matches the contract."""

    return bool(GENERATION_ID_PATTERN.fullmatch(value))


def validate_fingerprint(value: str) -> bool:
    """Return whether a value is canonical SHA-256 hexadecimal."""

    return bool(FINGERPRINT_PATTERN.fullmatch(value))
