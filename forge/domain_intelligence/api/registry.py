"""Analyzer registry for M4.4 API Domain Intelligence."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from forge.domain_intelligence.api.errors import (
    ApiConfigurationError,
)
from forge.domain_intelligence.api.models import ApiFinding

ApiAnalyzer = Callable[[Path], tuple[ApiFinding, ...]]


class ApiAnalyzerRegistry:
    """Deterministic registry of named API analyzers."""

    def __init__(
        self,
        analyzers: Iterable[
            tuple[str, ApiAnalyzer]
        ] = (),
    ) -> None:
        self._analyzers: dict[str, ApiAnalyzer] = {}

        for name, analyzer in analyzers:
            self.register(name, analyzer)

    def register(
        self,
        name: str,
        analyzer: ApiAnalyzer,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise ApiConfigurationError(
                "API analyzer name cannot be empty"
            )

        if normalized in self._analyzers:
            raise ApiConfigurationError(
                f"duplicate API analyzer: {normalized}"
            )

        self._analyzers[normalized] = analyzer

    def names(self) -> tuple[str, ...]:
        """Return analyzer names in deterministic order."""
        return tuple(sorted(self._analyzers))

    def analyze(
        self,
        project_root: Path,
    ) -> tuple[ApiFinding, ...]:
        """Run all analyzers and return stable findings."""
        findings: list[ApiFinding] = []

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