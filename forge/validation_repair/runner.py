"""Bounded subprocess runner for validation tools."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from forge.validation_repair.errors import (
    ValidationExecutionError,
    ValidationTimeoutError,
)
from forge.validation_repair.identifiers import validation_run_identifier
from forge.validation_repair.models import (
    ValidationCommand,
    ValidationRun,
    ValidationStatus,
    ValidationTool,
)
from forge.validation_repair.parser import parse_validation_output
from forge.validation_repair.policies import ValidationRepairPolicy


def _argv(command: ValidationCommand) -> list[str]:
    if command.tool is ValidationTool.RUFF:
        return [sys.executable, "-m", "ruff", "check", *command.arguments]
    if command.tool is ValidationTool.MYPY:
        return [sys.executable, "-m", "mypy", *command.arguments]
    if command.tool is ValidationTool.PYTEST:
        return [sys.executable, "-m", "pytest", *command.arguments]
    raise ValidationExecutionError(f"unsupported validation tool: {command.tool}")


def run_validation(
    repository_root: Path,
    command: ValidationCommand,
    policy: ValidationRepairPolicy,
) -> ValidationRun:
    """Execute one permitted validation command without a shell."""
    policy.validate_command(command)
    root = policy.resolve_repository(repository_root)
    argv = _argv(command)
    started = time.perf_counter()

    try:
        completed = subprocess.run(
            argv,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=command.timeout_seconds,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.perf_counter() - started
        raise ValidationTimeoutError(
            f"{command.tool.value} exceeded {command.timeout_seconds} seconds"
        ) from exc
    except OSError as exc:
        raise ValidationExecutionError(
            f"unable to execute {command.tool.value}: {exc}"
        ) from exc

    duration = time.perf_counter() - started
    findings = parse_validation_output(
        command.tool,
        completed.stdout,
        completed.stderr,
    )
    status = (
        ValidationStatus.PASSED
        if completed.returncode == 0
        else ValidationStatus.FAILED
    )
    run_id = validation_run_identifier(
        {
            "command_id": command.command_id,
            "tool": command.tool.value,
            "arguments": command.arguments,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    )
    return ValidationRun(
        run_id=run_id,
        command=command,
        status=status,
        exit_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_seconds=duration,
        findings=findings,
    )