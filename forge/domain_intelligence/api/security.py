"""API security analysis for M4.4."""

from __future__ import annotations

from forge.domain_intelligence.api.identifiers import (
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiAuthenticationKind,
    ApiContract,
    ApiFinding,
    ApiFindingSeverity,
)


def security_findings(
    contracts: tuple[ApiContract, ...],
) -> tuple[ApiFinding, ...]:
    """Identify conservative API authentication risks."""
    findings: list[ApiFinding] = []

    for contract in contracts:
        for endpoint in contract.endpoints:
            authentication = set(endpoint.authentication)

            if authentication and authentication != {
                ApiAuthenticationKind.NONE
            }:
                continue

            finding_id = api_finding_identifier(
                {
                    "category": "missing_authentication",
                    "endpoint_id": endpoint.endpoint_id,
                }
            )

            findings.append(
                ApiFinding(
                    finding_id=finding_id,
                    category="missing_authentication",
                    severity=ApiFindingSeverity.HIGH,
                    message=(
                        "No authentication requirement was detected "
                        f"for {endpoint.method.value} {endpoint.path}."
                    ),
                    path=endpoint.source_path,
                    evidence={
                        "method": endpoint.method.value,
                        "path": endpoint.path,
                    },
                )
            )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )