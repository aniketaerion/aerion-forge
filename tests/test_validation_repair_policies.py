from pathlib import Path

import pytest

from forge.validation_repair.errors import (
    InvalidValidationCommandError,
    RepairApprovalRequiredError,
)
from forge.validation_repair.models import ValidationCommand, ValidationTool
from forge.validation_repair.policies import ValidationRepairPolicy


def test_policy_defaults_are_bounded() -> None:
    policy = ValidationRepairPolicy()

    assert policy.max_repair_attempts == 3
    assert policy.dry_run_default is True
    assert policy.allow_shell is False


def test_policy_rejects_shell_metacharacters() -> None:
    command = ValidationCommand(
        command_id="cmd-1",
        tool=ValidationTool.PYTEST,
        arguments=("tests", "&&", "whoami"),
    )

    with pytest.raises(InvalidValidationCommandError):
        ValidationRepairPolicy().validate_command(command)


def test_policy_requires_approval_for_apply() -> None:
    with pytest.raises(RepairApprovalRequiredError):
        ValidationRepairPolicy().validate_apply_mode(
            dry_run=False,
            approved=False,
        )


def test_policy_resolves_existing_repository(tmp_path: Path) -> None:
    assert ValidationRepairPolicy.resolve_repository(tmp_path) == tmp_path.resolve()