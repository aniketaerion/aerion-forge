import pytest

from forge.autonomous_repair.errors import (
    RepairProviderConflictError,
    RepairProviderNotFoundError,
)
from forge.autonomous_repair.models import RepairProviderType
from forge.autonomous_repair.providers import ExactPatchProvider
from forge.autonomous_repair.registry import RepairProviderRegistry


def test_builtin_registry_is_deterministic() -> None:
    registry = RepairProviderRegistry.with_builtins()

    assert registry.list_provider_types() == (
        RepairProviderType.EXACT_PATCH,
        RepairProviderType.RUFF_FIX,
    )


def test_duplicate_provider_is_rejected() -> None:
    registry = RepairProviderRegistry()
    registry.register(ExactPatchProvider())

    with pytest.raises(RepairProviderConflictError):
        registry.register(ExactPatchProvider())


def test_missing_provider_is_rejected() -> None:
    with pytest.raises(RepairProviderNotFoundError):
        RepairProviderRegistry().get(RepairProviderType.RUFF_FIX)