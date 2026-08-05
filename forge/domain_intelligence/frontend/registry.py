"""Analyzer registry for M4.1 Frontend Intelligence."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from forge.domain_intelligence.errors import (
    DomainIntelligenceConfigurationError,
)
from forge.domain_intelligence.models import FrontendFinding

FrontendAnalyzer = Callable[[Path], tuple[FrontendFinding, ...]]


class FrontendAnalyzerRegistry:
    """Deterministic registry of named frontend analyzers."""

    def __init__(
        self,
        analyzers: Iterable[
            tuple[str, FrontendAnalyzer]
        ] = (),
    ) -> None:
        self._analyzers: dict[str, FrontendAnalyzer] = {}

        for name, analyzer in analyzers:
            self.register(name, analyzer)

    def register(
        self,
        name: str,
        analyzer: FrontendAnalyzer,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise DomainIntelligenceConfigurationError(
                "frontend analyzer name cannot be empty"
            )

        if normalized in self._analyzers:
            raise DomainIntelligenceConfigurationError(
                f"duplicate frontend analyzer: {normalized}"
            )

        self._analyzers[normalized] = analyzer

    def get(self, name: str) -> FrontendAnalyzer:
        normalized = name.strip().lower()

        try:
            return self._analyzers[normalized]
        except KeyError as exc:
            raise DomainIntelligenceConfigurationError(
                f"frontend analyzer not registered: {normalized}"
            ) from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._analyzers))

    def analyze(
        self,
        project_root: Path,
    ) -> tuple[FrontendFinding, ...]:
        findings: list[FrontendFinding] = []

        for name in self.names():
            findings.extend(self._analyzers[name](project_root))

        return tuple(
            sorted(
                findings,
                key=lambda finding: finding.finding_id,
            )
        )