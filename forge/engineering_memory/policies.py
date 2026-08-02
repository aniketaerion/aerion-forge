"""Deterministic Engineering Memory policies."""

from forge.engineering_memory.errors import (
    EngineeringMemoryValidationError,
)
from forge.engineering_memory.models import (
    MemoryConfidence,
    MemoryRetentionPolicy,
    MemoryType,
)

PERMANENT_MEMORY_TYPES = frozenset(
    {
        MemoryType.DECISION,
        MemoryType.APPROVAL,
        MemoryType.ENGINEERING_PATTERN,
        MemoryType.LESSON_LEARNED,
        MemoryType.RELEASE_EVIDENCE,
    }
)

VERIFIED_EVIDENCE_MEMORY_TYPES = frozenset(
    {
        MemoryType.DECISION,
        MemoryType.APPROVAL,
        MemoryType.RELEASE_EVIDENCE,
    }
)


def normalize_tag(value: str) -> str:
    """Normalize a memory tag into a stable representation."""

    normalized = "-".join(value.strip().casefold().split())

    if not normalized:
        raise EngineeringMemoryValidationError("Memory tag cannot be blank.")

    return normalized


def normalize_tags(
    values: tuple[str, ...],
) -> tuple[str, ...]:
    """Normalize, deduplicate and sort tags."""

    return tuple(sorted({normalize_tag(value) for value in values if value.strip()}))


def requires_permanent_retention(
    memory_type: MemoryType,
) -> bool:
    """Return whether a record should be permanently retained."""

    return memory_type in PERMANENT_MEMORY_TYPES


def requires_verified_evidence(
    memory_type: MemoryType,
) -> bool:
    """Return whether a record requires verified confidence."""

    return memory_type in VERIFIED_EVIDENCE_MEMORY_TYPES


def retention_policy_is_allowed(
    memory_type: MemoryType,
    retention_policy: MemoryRetentionPolicy,
) -> bool:
    """Return whether retention is valid for the record type."""

    if requires_permanent_retention(memory_type):
        return retention_policy is MemoryRetentionPolicy.PERMANENT

    return True


def confidence_is_allowed(
    memory_type: MemoryType,
    confidence: MemoryConfidence,
    *,
    allow_unknown: bool,
) -> bool:
    """Return whether confidence satisfies policy."""

    if confidence is MemoryConfidence.UNKNOWN and not allow_unknown:
        return False

    if requires_verified_evidence(memory_type):
        return confidence is MemoryConfidence.VERIFIED

    return True


def validate_memory_policy(
    *,
    memory_type: MemoryType,
    confidence: MemoryConfidence,
    retention_policy: MemoryRetentionPolicy,
    allow_unknown_confidence: bool,
    allow_temporary_records: bool,
) -> None:
    """Raise when a record violates Engineering Memory policy."""

    if not confidence_is_allowed(
        memory_type,
        confidence,
        allow_unknown=allow_unknown_confidence,
    ):
        raise EngineeringMemoryValidationError("Memory confidence violates the configured policy.")

    if not retention_policy_is_allowed(
        memory_type,
        retention_policy,
    ):
        raise EngineeringMemoryValidationError("Memory retention violates the record-type policy.")

    if retention_policy is MemoryRetentionPolicy.TEMPORARY and not allow_temporary_records:
        raise EngineeringMemoryValidationError("Temporary Engineering Memory records are disabled.")
