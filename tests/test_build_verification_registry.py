from pathlib import Path

import pytest

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.providers.base import BuildVerificationProvider
from forge.build_verification.registry import (
    BuildVerificationProviderRegistry,
)


class DuplicateProvider(BuildVerificationProvider):
    tool = VerificationTool.RUFF

    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        del step, repository_root, policy
        return ("python",)


def test_registry_returns_registered_provider() -> None:
    registry = BuildVerificationProviderRegistry()

    assert registry.get(VerificationTool.RUFF).tool is VerificationTool.RUFF


def test_registry_tools_are_sorted() -> None:
    registry = BuildVerificationProviderRegistry()
    values = tuple(tool.value for tool in registry.tools())

    assert values == tuple(sorted(values))


def test_registry_rejects_duplicate_tools() -> None:
    with pytest.raises(BuildVerificationProviderError):
        BuildVerificationProviderRegistry(
            (DuplicateProvider(), DuplicateProvider())
        )