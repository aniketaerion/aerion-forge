"""Analyzer registry for M4.3 Database Domain Intelligence."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from forge.domain_intelligence.database.errors import (
    DatabaseConfigurationError,
)
from forge.domain_intelligence.database.models import DatabaseFinding

DatabaseAnalyzer = Callable[[Path], tuple[DatabaseFinding, ...]]


class DatabaseAnalyzerRegistry:
    """Deterministic registry of named database analyzers."""

    def __init__(
        self,
        analyzers: Iterable[
            tuple[str, DatabaseAnalyzer]
        ] = (),
    ) -> None:
        self._analyzers: dict[str, DatabaseAnalyzer] = {}

        for name, analyzer in analyzers:
            self.register(name, analyzer)

    def register(
        self,
        name: str,
        analyzer: DatabaseAnalyzer,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise DatabaseConfigurationError(
                "database analyzer name cannot be empty"
            )

        if normalized in self._analyzers:
            raise DatabaseConfigurationError(
                f"duplicate database analyzer: {normalized}"
            )

        self._analyzers[normalized] = analyzer

    def names(self) -> tuple[str, ...]:
        """Return analyzer names in deterministic order."""
        return tuple(sorted(self._analyzers))

    def analyze(
        self,
        project_root: Path,
    ) -> tuple[DatabaseFinding, ...]:
        """Run all analyzers and return stable findings."""
        findings: list[DatabaseFinding] = []

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