"""Analyzer registry for M4.2 Backend Intelligence."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from forge.domain_intelligence.backend.errors import (
    BackendConfigurationError,
)
from forge.domain_intelligence.backend.models import BackendFinding

BackendAnalyzer = Callable[[Path], tuple[BackendFinding, ...]]


class BackendAnalyzerRegistry:
    """Deterministic registry of named backend analyzers."""

    def __init__(
        self,
        analyzers: Iterable[
            tuple[str, BackendAnalyzer]
        ] = (),
    ) -> None:
        self._analyzers: dict[str, BackendAnalyzer] = {}

        for name, analyzer in analyzers:
            self.register(name, analyzer)

    def register(
        self,
        name: str,
        analyzer: BackendAnalyzer,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise BackendConfigurationError(
                "backend analyzer name cannot be empty"
            )

        if normalized in self._analyzers:
            raise BackendConfigurationError(
                f"duplicate backend analyzer: {normalized}"
            )

        self._analyzers[normalized] = analyzer

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._analyzers))

    def analyze(
        self,
        project_root: Path,
    ) -> tuple[BackendFinding, ...]:
        findings: list[BackendFinding] = []

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