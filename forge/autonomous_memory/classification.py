"""Rule-based memory classification."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.models import MemoryObservation
from forge.autonomous_memory.normalization import normalize_statement
from forge.autonomous_memory.states import MemoryKind


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    memory_kind: MemoryKind
    rationale: str


_RULES = (
    (("failed", "failure", "regression", "error"), MemoryKind.FAILURE_PATTERN),
    (("rollback", "recovered", "recovery"), MemoryKind.RECOVERY_PATTERN),
    (("validation passed", "tests passed"), MemoryKind.VALIDATION_OUTCOME),
    (("execution completed", "execution succeeded"), MemoryKind.EXECUTION_OUTCOME),
    (("architecture", "must not", "constraint"), MemoryKind.ARCHITECTURE_CONSTRAINT),
    (("business rule", "customer requires"), MemoryKind.BUSINESS_RULE),
    (("decision", "selected"), MemoryKind.IMPLEMENTATION_DECISION),
    (("lesson", "best practice"), MemoryKind.ENGINEERING_LESSON),
    (("prefer", "preference"), MemoryKind.USER_PREFERENCE),
    (("maybe", "possibly", "hypothesis", "suspect"), MemoryKind.HYPOTHESIS),
)


def classify_observation(
    observation: MemoryObservation,
) -> ClassificationResult:
    normalized = normalize_statement(observation.content)

    for terms, memory_kind in _RULES:
        if any(term in normalized for term in terms):
            return ClassificationResult(
                memory_kind=memory_kind,
                rationale=f"Matched rules for {memory_kind.value}.",
            )

    if observation.evidence_references:
        return ClassificationResult(
            memory_kind=MemoryKind.REPOSITORY_FACT,
            rationale="Evidence-backed observation.",
        )

    return ClassificationResult(
        memory_kind=MemoryKind.HYPOTHESIS,
        rationale="Observation lacks supporting evidence.",
    )