from pathlib import Path

import pytest

from forge.domain_intelligence.backend.errors import (
    BackendConfigurationError,
)
from forge.domain_intelligence.backend.models import BackendFinding
from forge.domain_intelligence.backend.registry import (
    BackendAnalyzerRegistry,
)


def empty_analyzer(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    del project_root
    return ()


def test_backend_registry_names_are_sorted() -> None:
    registry = BackendAnalyzerRegistry(
        (
            ("node", empty_analyzer),
            ("django", empty_analyzer),
        )
    )

    assert registry.names() == ("django", "node")


def test_backend_registry_rejects_duplicates() -> None:
    with pytest.raises(BackendConfigurationError):
        BackendAnalyzerRegistry(
            (
                ("node", empty_analyzer),
                ("NODE", empty_analyzer),
            )
        )