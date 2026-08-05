"""Analyzer registry for M4.5 Business Domain Intelligence."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from forge.domain_intelligence.business_domain.errors import (
    BusinessDomainConfigurationError,
)
from forge.domain_intelligence.business_domain.models import (
    BusinessDomainFinding,
)

BusinessDomainAnalyzer = Callable[
    [Path],
    tuple[BusinessDomainFinding, ...],
]


class BusinessDomainAnalyzerRegistry:
    """Deterministic registry of business-domain analyzers."""

    def __init__(
        self,
        analyzers: Iterable[
            tuple[str, BusinessDomainAnalyzer]
        ] = (),
    ) -> None:
        self._analyzers: dict[
            str,
            BusinessDomainAnalyzer,
        ] = {}

        for name, analyzer in analyzers:
            self.register(name, analyzer)

    def register(
        self,
        name: str,
        analyzer: BusinessDomainAnalyzer,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise BusinessDomainConfigurationError(
                "business-domain analyzer name cannot be empty"
            )

        if normalized in self._analyzers:
            raise BusinessDomainConfigurationError(
                f"duplicate business-domain analyzer: {normalized}"
            )

        self._analyzers[normalized] = analyzer

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._analyzers))

    def analyze(
        self,
        project_root: Path,
    ) -> tuple[BusinessDomainFinding, ...]:
        findings: list[BusinessDomainFinding] = []

        for name in self.names():
            findings.extend(
                self._analyzers[name](project_root)
            )

        return tuple(
            sorted(
                findings,
                key=lambda finding: finding.finding_id,
            )
        )