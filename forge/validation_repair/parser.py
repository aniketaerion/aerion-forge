"""Parsers for Ruff, MyPy and Pytest validation output."""

from __future__ import annotations

import re

from forge.validation_repair.identifiers import stable_identifier
from forge.validation_repair.models import (
    FindingSeverity,
    ValidationFinding,
    ValidationTool,
)

_RUFF_LEGACY_PATTERN = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?P<column>\d+): "
    r"(?P<code>[A-Z]+\d+) (?P<message>.+)$"
)

_RUFF_CODE_PATTERN = re.compile(
    r"^(?P<code>[A-Z]+\d+)(?:\s+\[\*\])?\s+(?P<message>.+)$"
)

_RUFF_LOCATION_PATTERN = re.compile(
    r"^\s*-->\s+(?P<path>.+?):(?P<line>\d+):(?P<column>\d+)\s*$"
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
    """Parse legacy and current Ruff text output."""
    findings: list[ValidationFinding] = []
    lines = output.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index].strip()

        legacy = _RUFF_LEGACY_PATTERN.match(line)
        if legacy:
            findings.append(
                _finding(
                    tool=ValidationTool.RUFF,
                    severity=FindingSeverity.ERROR,
                    code=legacy.group("code"),
                    message=legacy.group("message"),
                    path=legacy.group("path"),
                    line=int(legacy.group("line")),
                    column=int(legacy.group("column")),
                )
            )
            index += 1
            continue

        code_match = _RUFF_CODE_PATTERN.match(line)
        if code_match:
            location_match = None

            for candidate_index in range(
                index + 1,
                min(index + 5, len(lines)),
            ):
                location_match = _RUFF_LOCATION_PATTERN.match(
                    lines[candidate_index]
                )
                if location_match:
                    break

            if location_match:
                findings.append(
                    _finding(
                        tool=ValidationTool.RUFF,
                        severity=FindingSeverity.ERROR,
                        code=code_match.group("code"),
                        message=code_match.group("message"),
                        path=location_match.group("path"),
                        line=int(location_match.group("line")),
                        column=int(location_match.group("column")),
                    )
                )

        index += 1

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
    combined = "\n".join(
        part for part in (stdout, stderr) if part
    )

    if tool is ValidationTool.RUFF:
        return parse_ruff_output(combined)

    if tool is ValidationTool.MYPY:
        return parse_mypy_output(combined)

    if tool is ValidationTool.PYTEST:
        return parse_pytest_output(combined)

    return ()