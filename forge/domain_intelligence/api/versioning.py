"""API version analysis for M4.4."""

from __future__ import annotations

import re

from forge.domain_intelligence.api.identifiers import (
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiFinding,
    ApiFindingSeverity,
)

_PATH_VERSION_PATTERN = re.compile(
    r"/v(?P<version>[0-9]+)(?:/|$)",
    re.IGNORECASE,
)


def contract_versions(
    contracts: tuple[ApiContract, ...],
) -> tuple[str, ...]:
    """Return declared and path-derived API versions."""
    versions: set[str] = set()

    for contract in contracts:
        if contract.version:
            versions.add(contract.version)

        for endpoint in contract.endpoints:
            match = _PATH_VERSION_PATTERN.search(endpoint.path)
            if match is not None:
                versions.add(match.group("version"))

    return tuple(sorted(versions))


def versioning_findings(
    contracts: tuple[ApiContract, ...],
) -> tuple[ApiFinding, ...]:
    """Report missing or inconsistent API versioning."""
    versions = contract_versions(contracts)

    if not contracts:
        return ()

    findings: list[ApiFinding] = []

    if not versions:
        finding_id = api_finding_identifier(
            {"category": "missing_versioning"}
        )
        findings.append(
            ApiFinding(
                finding_id=finding_id,
                category="missing_versioning",
                severity=ApiFindingSeverity.MEDIUM,
                message="No API versioning signal was detected.",
            )
        )

    if len(versions) > 1:
        finding_id = api_finding_identifier(
            {
                "category": "multiple_versions",
                "versions": versions,
            }
        )
        findings.append(
            ApiFinding(
                finding_id=finding_id,
                category="multiple_versions",
                severity=ApiFindingSeverity.INFO,
                message="Multiple API versions were detected.",
                evidence={"versions": ",".join(versions)},
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )