"""Provenance and evidence digest creation."""

from __future__ import annotations

import hashlib
import json

from forge.autonomous_memory.identifiers import memory_provenance_identifier
from forge.autonomous_memory.models import MemoryObservation, MemoryProvenance


def evidence_digest(values: tuple[str, ...]) -> str:
    canonical = json.dumps(
        sorted(set(values)),
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_provenance(
    *,
    memory_id: str,
    observation: MemoryObservation,
    actor: str,
) -> MemoryProvenance:
    digest = evidence_digest(observation.evidence_references)
    payload = {
        "memory_id": memory_id,
        "source_kind": observation.source_kind.value,
        "source_reference": observation.source_reference,
        "repository_fingerprint": observation.repository_fingerprint,
        "evidence_digest": digest,
        "actor": actor,
    }

    return MemoryProvenance(
        provenance_id=memory_provenance_identifier(payload),
        memory_id=memory_id,
        source_kind=observation.source_kind,
        source_reference=observation.source_reference,
        evidence_digest=digest,
        repository_fingerprint=observation.repository_fingerprint,
        actor=actor,
    )