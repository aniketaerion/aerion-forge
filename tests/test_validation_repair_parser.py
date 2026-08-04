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