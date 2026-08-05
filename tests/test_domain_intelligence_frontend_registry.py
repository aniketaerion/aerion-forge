from pathlib import Path

import pytest

from forge.domain_intelligence.errors import (
    DomainIntelligenceConfigurationError,
)
from forge.domain_intelligence.frontend.registry import (
    FrontendAnalyzerRegistry,
)
from forge.domain_intelligence.models import FrontendFinding


def empty_analyzer(
    project_root: Path,
) -> tuple[FrontendFinding, ...]:
    del project_root
    return ()


def test_registry_names_are_deterministic() -> None:
    registry = FrontendAnalyzerRegistry(
        (
            ("vite", empty_analyzer),
            ("react", empty_analyzer),
        )
    )

    assert registry.names() == ("react", "vite")


def test_registry_rejects_duplicate_name() -> None:
    with pytest.raises(DomainIntelligenceConfigurationError):
        FrontendAnalyzerRegistry(
            (
                ("react", empty_analyzer),
                ("REACT", empty_analyzer),
            )
        )