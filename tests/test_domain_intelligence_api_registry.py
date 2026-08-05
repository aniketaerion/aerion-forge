from pathlib import Path

import pytest

from forge.domain_intelligence.api.errors import (
    ApiConfigurationError,
)
from forge.domain_intelligence.api.models import ApiFinding
from forge.domain_intelligence.api.registry import (
    ApiAnalyzerRegistry,
)


def empty_analyzer(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    del project_root
    return ()


def test_api_registry_names_are_sorted() -> None:
    registry = ApiAnalyzerRegistry(
        (
            ("rest", empty_analyzer),
            ("openapi", empty_analyzer),
        )
    )

    assert registry.names() == (
        "openapi",
        "rest",
    )


def test_api_registry_rejects_duplicates() -> None:
    with pytest.raises(ApiConfigurationError):
        ApiAnalyzerRegistry(
            (
                ("rest", empty_analyzer),
                ("REST", empty_analyzer),
            )
        )