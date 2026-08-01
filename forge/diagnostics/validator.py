"""Validation and deterministic aggregation for diagnostics."""

from collections import Counter

from forge.diagnostics.errors import DiagnosticCycleError, DiagnosticDefinitionError
from forge.diagnostics.models import (
    DiagnosticCriticality,
    DiagnosticDefinition,
    DiagnosticResult,
    DiagnosticStatistics,
    DiagnosticSummary,
    DiagnosticValidationResult,
    HealthStatus,
)


def validate_definitions(
    definitions: tuple[DiagnosticDefinition, ...],
    configuration_keys: set[str] | None = None,
    capability_ids: set[str] | None = None,
) -> DiagnosticValidationResult:
    errors: list[str] = []
    by_id = {item.check_id: item for item in definitions}
    if len(by_id) != len(definitions):
        errors.append("duplicate diagnostic check ID")
    for item in definitions:
        for prerequisite in item.prerequisite_checks:
            if prerequisite not in by_id:
                errors.append(f"unknown prerequisite {prerequisite} for {item.check_id}")
            if prerequisite == item.check_id:
                errors.append(f"self dependency for {item.check_id}")
        if configuration_keys is not None:
            for key in item.required_configuration_keys:
                if key not in configuration_keys:
                    errors.append(f"unknown configuration key {key}")
        if capability_ids is not None:
            for capability_id in item.required_capabilities:
                if capability_id not in capability_ids:
                    errors.append(f"unknown capability ID {capability_id}")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(check_id: str) -> None:
        if check_id in visiting:
            raise DiagnosticCycleError(f"diagnostic prerequisite cycle at {check_id}")
        if check_id in visited:
            return
        visiting.add(check_id)
        for dependency in by_id[check_id].prerequisite_checks:
            if dependency in by_id:
                visit(dependency)
        visiting.remove(check_id)
        visited.add(check_id)

    try:
        for check_id in sorted(by_id):
            visit(check_id)
    except DiagnosticCycleError as exc:
        errors.append(str(exc))
    return DiagnosticValidationResult(valid=not errors, errors=tuple(sorted(set(errors))))


def require_valid_definitions(definitions: tuple[DiagnosticDefinition, ...]) -> None:
    result = validate_definitions(definitions)
    if not result.valid:
        raise DiagnosticDefinitionError("; ".join(result.errors))


def aggregate(results: tuple[DiagnosticResult, ...], strict: bool = False) -> DiagnosticSummary:
    counts = Counter(item.status.value for item in results)
    required = [item for item in results if item.criticality is DiagnosticCriticality.REQUIRED]
    recommended = [
        item for item in results if item.criticality is DiagnosticCriticality.RECOMMENDED
    ]
    if any(item.status is HealthStatus.UNHEALTHY or item.blocking for item in required):
        overall = HealthStatus.UNHEALTHY
    elif (strict and any(
        item.status in {HealthStatus.UNKNOWN, HealthStatus.SKIPPED} for item in required
    )) or any(item.status is HealthStatus.UNKNOWN for item in required):
        overall = HealthStatus.UNKNOWN
    elif any(
        item.status in {HealthStatus.DEGRADED, HealthStatus.UNHEALTHY, HealthStatus.UNKNOWN}
        for item in recommended
    ) or any(item.status is HealthStatus.DEGRADED for item in required):
        overall = HealthStatus.DEGRADED
    elif results and all(
        item.status in {HealthStatus.HEALTHY, HealthStatus.NOT_APPLICABLE}
        for item in results
        if item.criticality is not DiagnosticCriticality.OPTIONAL
    ):
        overall = HealthStatus.HEALTHY
    else:
        overall = HealthStatus.UNKNOWN
    return DiagnosticSummary(
        overall_status=overall,
        total_checks=len(results),
        healthy_count=counts[HealthStatus.HEALTHY.value],
        degraded_count=counts[HealthStatus.DEGRADED.value],
        unhealthy_count=counts[HealthStatus.UNHEALTHY.value],
        unknown_count=counts[HealthStatus.UNKNOWN.value],
        not_applicable_count=counts[HealthStatus.NOT_APPLICABLE.value],
        skipped_count=counts[HealthStatus.SKIPPED.value],
        blocking_count=sum(item.blocking for item in results),
        actionable_count=sum(bool(item.corrective_actions) for item in results),
    )


def statistics(results: tuple[DiagnosticResult, ...]) -> DiagnosticStatistics:
    def count(attribute: str) -> dict[str, int]:
        values = Counter(getattr(item, attribute).value for item in results)
        return dict(sorted(values.items()))

    return DiagnosticStatistics(
        total_checks=len(results),
        checks_by_status=count("status"),
        checks_by_category=count("category"),
        checks_by_scope=count("scope"),
        checks_by_severity=count("severity"),
        checks_by_criticality=count("criticality"),
        blocking_checks=sum(item.blocking for item in results),
        actionable_checks=sum(bool(item.corrective_actions) for item in results),
        checks_with_warnings=sum(item.severity.value == "warning" for item in results),
        checks_with_errors=sum(item.severity.value in {"error", "critical"} for item in results),
    )
