[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

Write-Utf8NoBom "forge\validation_repair\parser.py" @'
"""Parsers for Ruff, MyPy and Pytest validation output."""

from __future__ import annotations

import re

from forge.validation_repair.identifiers import stable_identifier
from forge.validation_repair.models import (
    FindingSeverity,
    ValidationFinding,
    ValidationTool,
)


_RUFF_PATTERN = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+): "
    r"(?P<code>[A-Z]+\d+) (?P<message>.+)$"
)

_MYPY_PATTERN = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+): "
    r"(?P<severity>error|note): (?P<message>.+?)"
    r"(?:\s+\[(?P<code>[^\]]+)\])?$"
)

_PYTEST_PATTERN = re.compile(
    r"^(?P<path>[^:]+)::(?P<test_name>\S+)\s+-\s+(?P<message>.+)$"
)


def _finding(
    *,
    tool: ValidationTool,
    severity: FindingSeverity,
    code: str,
    message: str,
    path: str | None = None,
    line: int | None = None,
    column: int | None = None,
) -> ValidationFinding:
    finding_id = stable_identifier(
        "valfind",
        {
            "tool": tool.value,
            "severity": severity.value,
            "code": code,
            "message": message,
            "path": path,
            "line": line,
            "column": column,
        },
    )
    return ValidationFinding(
        finding_id=finding_id,
        tool=tool,
        severity=severity,
        code=code,
        message=message,
        path=path,
        line=line,
        column=column,
    )


def parse_ruff_output(output: str) -> tuple[ValidationFinding, ...]:
    """Parse Ruff text output."""
    findings: list[ValidationFinding] = []
    for line in output.splitlines():
        match = _RUFF_PATTERN.match(line.strip())
        if not match:
            continue
        findings.append(
            _finding(
                tool=ValidationTool.RUFF,
                severity=FindingSeverity.ERROR,
                code=match.group("code"),
                message=match.group("message"),
                path=match.group("path"),
                line=int(match.group("line")),
                column=int(match.group("column")),
            )
        )
    return tuple(findings)


def parse_mypy_output(output: str) -> tuple[ValidationFinding, ...]:
    """Parse MyPy text output."""
    findings: list[ValidationFinding] = []
    for line in output.splitlines():
        match = _MYPY_PATTERN.match(line.strip())
        if not match:
            continue
        severity = (
            FindingSeverity.ERROR
            if match.group("severity") == "error"
            else FindingSeverity.INFO
        )
        findings.append(
            _finding(
                tool=ValidationTool.MYPY,
                severity=severity,
                code=match.group("code") or match.group("severity"),
                message=match.group("message"),
                path=match.group("path"),
                line=int(match.group("line")),
            )
        )
    return tuple(findings)


def parse_pytest_output(output: str) -> tuple[ValidationFinding, ...]:
    """Parse Pytest short-summary failures."""
    findings: list[ValidationFinding] = []
    for line in output.splitlines():
        match = _PYTEST_PATTERN.match(line.strip())
        if not match:
            continue
        findings.append(
            _finding(
                tool=ValidationTool.PYTEST,
                severity=FindingSeverity.ERROR,
                code="pytest-failure",
                message=match.group("message"),
                path=match.group("path"),
            )
        )
    return tuple(findings)


def parse_validation_output(
    tool: ValidationTool,
    stdout: str,
    stderr: str,
) -> tuple[ValidationFinding, ...]:
    """Parse combined output for one supported tool."""
    combined = "\n".join(part for part in (stdout, stderr) if part)
    if tool is ValidationTool.RUFF:
        return parse_ruff_output(combined)
    if tool is ValidationTool.MYPY:
        return parse_mypy_output(combined)
    if tool is ValidationTool.PYTEST:
        return parse_pytest_output(combined)
    return ()
'@

Write-Utf8NoBom "forge\validation_repair\runner.py" @'
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
'@

Write-Utf8NoBom "tests\test_validation_repair_parser.py" @'
from forge.validation_repair.models import FindingSeverity, ValidationTool
from forge.validation_repair.parser import (
    parse_mypy_output,
    parse_pytest_output,
    parse_ruff_output,
)


def test_parse_ruff_output() -> None:
    findings = parse_ruff_output(
        "forge/app.py:10:5: F401 unused import\n"
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.tool is ValidationTool.RUFF
    assert finding.code == "F401"
    assert finding.path == "forge/app.py"
    assert finding.line == 10
    assert finding.column == 5


def test_parse_mypy_output() -> None:
    findings = parse_mypy_output(
        'forge/app.py:12: error: Incompatible types [assignment]\n'
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.tool is ValidationTool.MYPY
    assert finding.code == "assignment"
    assert finding.severity is FindingSeverity.ERROR
    assert finding.line == 12


def test_parse_pytest_output() -> None:
    findings = parse_pytest_output(
        "tests/test_app.py::test_value - AssertionError: expected 1\n"
    )

    assert len(findings) == 1
    finding = findings[0]
    assert finding.tool is ValidationTool.PYTEST
    assert finding.code == "pytest-failure"
    assert finding.path == "tests/test_app.py"


def test_parser_ignores_unrecognized_lines() -> None:
    assert parse_ruff_output("All checks passed!") == ()
    assert parse_mypy_output("Success: no issues found") == ()
    assert parse_pytest_output("10 passed in 0.10s") == ()
'@

Write-Utf8NoBom "tests\test_validation_repair_runner.py" @'
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
'@

Write-Host ""
Write-Host "Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest `
    .\tests\test_validation_repair_runner.py `
    .\tests\test_validation_repair_parser.py `
    -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "M3.4 PACKAGE 1 COMPLETE" -ForegroundColor Green
git status --short