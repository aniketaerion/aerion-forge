from pathlib import Path

import pytest

from forge.autonomous_repair.errors import (
    RepairApprovalRequiredError,
    RepairPolicyViolationError,
)
from forge.autonomous_repair.models import RepairProviderType
from forge.autonomous_repair.policies import AutonomousRepairPolicy


def test_policy_defaults_are_bounded() -> None:
    policy = AutonomousRepairPolicy()
    assert policy.max_attempts == 3
    assert policy.dry_run_default is True
    assert policy.allow_shell is False
    assert policy.allow_git_mutation is False


def test_policy_rejects_unapproved_apply() -> None:
    with pytest.raises(RepairApprovalRequiredError):
        AutonomousRepairPolicy().validate_apply_mode(
            dry_run=False,
            approved=False,
        )


def test_policy_rejects_protected_path() -> None:
    with pytest.raises(RepairPolicyViolationError):
        AutonomousRepairPolicy().validate_paths((".git/config",))


def test_policy_accepts_registered_provider() -> None:
    AutonomousRepairPolicy().validate_provider(
        RepairProviderType.EXACT_PATCH
    )


def test_policy_resolves_existing_repository(tmp_path: Path) -> None:
    assert AutonomousRepairPolicy.resolve_repository(tmp_path) == tmp_path.resolve()