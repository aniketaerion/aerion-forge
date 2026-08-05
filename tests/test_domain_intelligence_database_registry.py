from pathlib import Path

import pytest

from forge.domain_intelligence.database.errors import (
    DatabaseConfigurationError,
)
from forge.domain_intelligence.database.models import DatabaseFinding
from forge.domain_intelligence.database.registry import (
    DatabaseAnalyzerRegistry,
)


def empty_analyzer(
    project_root: Path,
) -> tuple[DatabaseFinding, ...]:
    del project_root
    return ()


def test_database_registry_names_are_sorted() -> None:
    registry = DatabaseAnalyzerRegistry(
        (
            ("postgres", empty_analyzer),
            ("configuration", empty_analyzer),
        )
    )

    assert registry.names() == (
        "configuration",
        "postgres",
    )


def test_database_registry_rejects_duplicates() -> None:
    with pytest.raises(DatabaseConfigurationError):
        DatabaseAnalyzerRegistry(
            (
                ("postgres", empty_analyzer),
                ("POSTGRES", empty_analyzer),
            )
        )