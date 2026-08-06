"""Memory observation ingestion service."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.classification import (
    ClassificationResult,
    classify_observation,
)
from forge.autonomous_memory.confidence import (
    ConfidenceAssessment,
    assess_initial_confidence,
)
from forge.autonomous_memory.errors import (
    MemoryContractError,
    MemoryRedactionError,
)
from forge.autonomous_memory.identifiers import memory_record_identifier
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryObservation,
    MemoryProvenance,
    MemoryRecord,
)
from forge.autonomous_memory.normalization import (
    normalize_scope,
    normalize_statement,
    normalize_tags,
)
from forge.autonomous_memory.policies import AutonomousMemoryPolicy
from forge.autonomous_memory.provenance import build_provenance
from forge.autonomous_memory.redaction import redact_prohibited_content
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    record: MemoryRecord
    provenance: MemoryProvenance
    classification: ClassificationResult
    confidence: ConfidenceAssessment


@dataclass(frozen=True, slots=True)
class MemoryIngestionService:
    policy: AutonomousMemoryPolicy

    def ingest(
        self,
        observation: MemoryObservation,
        *,
        actor: str,
        memory_kind: MemoryKind | None = None,
        module_scope: tuple[str, ...] = (),
        capability_scope: tuple[str, ...] = (),
        business_domain: str | None = None,
    ) -> IngestionResult:
        if not actor.strip():
            raise MemoryContractError("Actor cannot be empty.")

        if (
            len(observation.content)
            > self.policy.limits.maximum_observation_characters
        ):
            raise MemoryContractError(
                "Observation exceeds configured size limit."
            )

        if len(observation.tags) > self.policy.limits.maximum_tags:
            raise MemoryContractError(
                "Observation exceeds configured tag limit."
            )

        redaction = redact_prohibited_content(observation.content)

        if (
            self.policy.safety.reject_secrets
            and redaction.detected_categories
        ):
            raise MemoryRedactionError(
                "Prohibited content detected: "
                + ", ".join(redaction.detected_categories)
            )

        normalized = normalize_statement(redaction.content)
        if not normalized:
            raise MemoryContractError(
                "Normalized statement cannot be empty."
            )

        classification = (
            ClassificationResult(
                memory_kind=memory_kind,
                rationale="Memory kind supplied explicitly.",
            )
            if memory_kind is not None
            else classify_observation(observation)
        )

        confidence = assess_initial_confidence(
            observation=observation,
            memory_kind=classification.memory_kind,
        )

        if (
            classification.memory_kind
            is MemoryKind.REPOSITORY_FACT
            and confidence.score
            < self.policy.confidence.minimum_fact_confidence
        ):
            classification = ClassificationResult(
                memory_kind=MemoryKind.HYPOTHESIS,
                rationale=(
                    "Fact confidence below policy threshold."
                ),
            )
            confidence = assess_initial_confidence(
                observation=observation,
                memory_kind=MemoryKind.HYPOTHESIS,
            )

        memory_id = memory_record_identifier(
            {
                "repository_scope": observation.repository_root,
                "memory_kind": classification.memory_kind.value,
                "normalized_statement": normalized,
                "source_reference": observation.source_reference,
                "repository_fingerprint": (
                    observation.repository_fingerprint
                ),
            }
        )

        applicability = MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope=observation.repository_root,
            module_scope=normalize_scope(module_scope),
            capability_scope=normalize_scope(capability_scope),
            business_domain=business_domain,
            rationale="Repository-scoped by default.",
        )

        record = MemoryRecord(
            memory_id=memory_id,
            memory_kind=classification.memory_kind,
            statement=redaction.content.strip(),
            normalized_statement=normalized,
            confidence=confidence.score,
            repository_scope=observation.repository_root,
            module_scope=normalize_scope(module_scope),
            capability_scope=normalize_scope(capability_scope),
            business_domain=business_domain,
            evidence_references=tuple(
                sorted(set(observation.evidence_references))
            ),
            source_references=(observation.source_reference,),
            tags=normalize_tags(observation.tags),
            applicability=applicability,
            retention_class=_retention_for_kind(
                classification.memory_kind
            ),
        )

        provenance = build_provenance(
            memory_id=memory_id,
            observation=observation,
            actor=actor.strip(),
        )

        return IngestionResult(
            record=record,
            provenance=provenance,
            classification=classification,
            confidence=confidence,
        )


def _retention_for_kind(
    memory_kind: MemoryKind,
) -> RetentionClass:
    if memory_kind in {
        MemoryKind.ARCHITECTURE_CONSTRAINT,
        MemoryKind.BUSINESS_RULE,
    }:
        return RetentionClass.PERMANENT

    if memory_kind in {
        MemoryKind.ENGINEERING_LESSON,
        MemoryKind.FAILURE_PATTERN,
        MemoryKind.RECOVERY_PATTERN,
        MemoryKind.NEGATIVE_EVIDENCE,
    }:
        return RetentionClass.LONG_LIVED

    if memory_kind is MemoryKind.HYPOTHESIS:
        return RetentionClass.TEMPORARY

    return RetentionClass.PROJECT_LIFETIME