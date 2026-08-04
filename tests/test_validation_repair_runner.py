from pathlib import Path

import pytest

from forge.validation_repair.errors import InvalidValidationCommandError
from forge.validation_repair.models import (
    ValidationCommand,
    ValidationStatus,
    ValidationTool,
)
from forge.validation_repair.policies import ValidationRepairPolicy
from forge.validation_repair.runner import run_validation


def test_runner_executes_passing_pytest(tmp_path: Path) -> None:
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        "def test_ok() -> None:\n    assert 1 == 1\n",
        encoding="utf-8",
    )
    command = ValidationCommand(
        command_id="pytest-pass",
        tool=ValidationTool.PYTEST,
        arguments=("-q", "test_sample.py"),
        timeout_seconds=30,
    )

    result = run_validation(tmp_path, command, ValidationRepairPolicy())

    assert result.status is ValidationStatus.PASSED
    assert result.exit_code == 0
    assert result.findings == ()


def test_runner_returns_failed_pytest_finding(tmp_path: Path) -> None:
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        "def test_bad() -> None:\n    assert 1 == 2\n",
        encoding="utf-8",
    )
    command = ValidationCommand(
        command_id="pytest-fail",
        tool=ValidationTool.PYTEST,
        arguments=("-q", "test_sample.py"),
        timeout_seconds=30,
    )

    result = run_validation(tmp_path, command, ValidationRepairPolicy())

    assert result.status is ValidationStatus.FAILED
    assert result.exit_code != 0


def test_runner_rejects_shell_metacharacters(tmp_path: Path) -> None:
    command = ValidationCommand(
        command_id="unsafe",
        tool=ValidationTool.PYTEST,
        arguments=("tests", "&&", "whoami"),
    )

    with pytest.raises(InvalidValidationCommandError):
        run_validation(tmp_path, command, ValidationRepairPolicy())


def test_runner_executes_ruff(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("import os\n", encoding="utf-8")
    command = ValidationCommand(
        command_id="ruff-fail",
        tool=ValidationTool.RUFF,
        arguments=("sample.py",),
        timeout_seconds=30,
    )

    result = run_validation(tmp_path, command, ValidationRepairPolicy())

    assert result.status is ValidationStatus.FAILED
    assert any(finding.code == "F401" for finding in result.findings)