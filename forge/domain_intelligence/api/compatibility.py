"""API compatibility analysis for M4.4."""

from __future__ import annotations

from forge.domain_intelligence.api.identifiers import (
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiFinding,
    ApiFindingSeverity,
)


def compatibility_findings(
    contracts: tuple[ApiContract, ...],
) -> tuple[ApiFinding, ...]:
    """Identify duplicate method-path contracts and operation identifiers."""
    findings: list[ApiFinding] = []
    route_owners: dict[tuple[str, str], list[str]] = {}
    operation_owners: dict[str, list[str]] = {}

    for contract in contracts:
        for endpoint in contract.endpoints:
            key = (endpoint.method.value, endpoint.path)
            route_owners.setdefault(key, []).append(
                contract.contract_id
            )

            if endpoint.operation_id:
                operation_owners.setdefault(
                    endpoint.operation_id,
                    [],
                ).append(endpoint.endpoint_id)

    for (method, path), owners in sorted(route_owners.items()):
        if len(owners) <= 1:
            continue

        finding_id = api_finding_identifier(
            {
                "category": "duplicate_route_contract",
                "method": method,
                "path": path,
                "owners": owners,
            }
        )
        findings.append(
            ApiFinding(
                finding_id=finding_id,
                category="duplicate_route_contract",
                severity=ApiFindingSeverity.MEDIUM,
                message=(
                    "The same method and path appear in multiple "
                    "API contracts."
                ),
                evidence={
                    "method": method,
                    "path": path,
                    "contract_count": str(len(owners)),
                },
            )
        )

    for operation_id, endpoint_ids in sorted(
        operation_owners.items()
    ):
        if len(endpoint_ids) <= 1:
            continue

        finding_id = api_finding_identifier(
            {
                "category": "duplicate_operation_id",
                "operation_id": operation_id,
                "endpoint_ids": endpoint_ids,
            }
        )
        findings.append(
            ApiFinding(
                finding_id=finding_id,
                category="duplicate_operation_id",
                severity=ApiFindingSeverity.HIGH,
                message="Duplicate API operation identifier detected.",
                evidence={
                    "operation_id": operation_id,
                    "endpoint_count": str(len(endpoint_ids)),
                },
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )