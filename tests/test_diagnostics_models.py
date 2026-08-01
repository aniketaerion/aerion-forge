"""Diagnostics model, aggregation, registry, and query coverage."""

import pytest
from pydantic import ValidationError

from forge.diagnostics.errors import DiagnosticNotFoundError
from forge.diagnostics.models import (
    CorrectiveAction,
    DiagnosticCategory,
    DiagnosticCriticality,
    DiagnosticDefinition,
    DiagnosticEvidence,
    DiagnosticResult,
    DiagnosticScope,
    DiagnosticSeverity,
    HealthStatus,
)
from forge.diagnostics.registry import DIAGNOSTIC_REGISTRY
from forge.diagnostics.validator import aggregate, validate_definitions


def definition(check_id: str = "sample-check") -> DiagnosticDefinition:
    return DiagnosticDefinition(
        check_id=check_id,
        display_name="Sample",
        description="Sample diagnostic.",
        category=DiagnosticCategory.CORE,
        scope=DiagnosticScope.RUNTIME,
        criticality=DiagnosticCriticality.REQUIRED,
    )


def diagnostic(
    status: HealthStatus,
    *,
    criticality: DiagnosticCriticality = DiagnosticCriticality.REQUIRED,
) -> DiagnosticResult:
    return DiagnosticResult(
        check_id="sample-check",
        display_name="Sample",
        status=status,
        severity=(
            DiagnosticSeverity.ERROR
            if status is HealthStatus.UNHEALTHY
            else DiagnosticSeverity.INFO
        ),
        category=DiagnosticCategory.CORE,
        scope=DiagnosticScope.RUNTIME,
        criticality=criticality,
        summary="Result.",
        blocking=status is HealthStatus.UNHEALTHY and criticality is DiagnosticCriticality.REQUIRED,
    )


def test_models_reject_invalid_ids_duplicates_and_unredacted_sensitive_evidence() -> None:
    with pytest.raises(ValidationError):
        definition("Not Canonical")
    with pytest.raises(ValidationError):
        DiagnosticEvidence(
            evidence_id="secret", label="Secret", safe_value="token", source="test", sensitive=True
        )
    evidence = DiagnosticEvidence(evidence_id="same", label="One", safe_value="safe", source="test")
    with pytest.raises(ValidationError):
        DiagnosticResult(
            **diagnostic(HealthStatus.HEALTHY).model_dump(exclude={"evidence"}),
            evidence=(evidence, evidence),
        )
    action = CorrectiveAction(action_id="same", title="Review", description="Review state.")
    with pytest.raises(ValidationError):
        DiagnosticResult(
            **diagnostic(HealthStatus.UNHEALTHY).model_dump(exclude={"corrective_actions"}),
            corrective_actions=(action, action),
        )


def test_registry_is_complete_sorted_and_cycle_free() -> None:
    checks = DIAGNOSTIC_REGISTRY.list_checks()
    identifiers = [item.check_id for item in checks]
    assert len(checks) == 30
    assert identifiers == sorted(identifiers)
    assert len(identifiers) == len(set(identifiers))
    assert validate_definitions(checks).valid
    with pytest.raises(DiagnosticNotFoundError):
        DIAGNOSTIC_REGISTRY.get_check("missing-check")


@pytest.mark.parametrize(
    ("results", "strict", "expected"),
    [
        ((diagnostic(HealthStatus.HEALTHY),), False, HealthStatus.HEALTHY),
        ((diagnostic(HealthStatus.UNHEALTHY),), False, HealthStatus.UNHEALTHY),
        ((diagnostic(HealthStatus.UNKNOWN),), False, HealthStatus.UNKNOWN),
        ((diagnostic(HealthStatus.SKIPPED),), True, HealthStatus.UNKNOWN),
        (
            (
                diagnostic(
                    HealthStatus.DEGRADED,
                    criticality=DiagnosticCriticality.RECOMMENDED,
                ),
            ),
            False,
            HealthStatus.DEGRADED,
        ),
        ((diagnostic(HealthStatus.NOT_APPLICABLE),), False, HealthStatus.HEALTHY),
    ],
)
def test_aggregation_statuses(
    results: tuple[DiagnosticResult, ...], strict: bool, expected: HealthStatus
) -> None:
    assert aggregate(results, strict).overall_status is expected
