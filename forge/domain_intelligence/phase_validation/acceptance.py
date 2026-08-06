"""Acceptance-criteria validation for M4.8 Package 1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.phase_validation.identifiers import (
    phase_validation_check_identifier,
    phase_validation_result_identifier,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationCheck,
    PhaseValidationKind,
    PhaseValidationResult,
    PhaseValidationStatus,
)


def acceptance_check() -> PhaseValidationCheck:
    payload = {
        "name": "Acceptance criteria validation",
        "kind": PhaseValidationKind.ACCEPTANCE.value,
    }
    return PhaseValidationCheck(
        check_id=phase_validation_check_identifier(payload),
        name="Acceptance criteria validation",
        kind=PhaseValidationKind.ACCEPTANCE,
        description=(
            "Verify that milestone acceptance criteria exist and "
            "contain actionable entries."
        ),
    )


def validate_acceptance_criteria(
    repository_root: Path,
) -> PhaseValidationResult:
    check = acceptance_check()
    path = (
        repository_root
        / "docs"
        / "domain_intelligence"
        / "phase_validation"
        / "ACCEPTANCE_CRITERIA.md"
    )

    content = (
        path.read_text(encoding="utf-8")
        if path.is_file()
        else ""
    )
    actionable_lines = tuple(
        line
        for line in content.splitlines()
        if line.strip().startswith("- ")
    )
    passed = bool(actionable_lines)
    status = (
        PhaseValidationStatus.PASS
        if passed
        else PhaseValidationStatus.FAIL
    )
    payload = {
        "check_id": check.check_id,
        "status": status.value,
        "item_count": len(actionable_lines),
    }

    return PhaseValidationResult(
        result_id=phase_validation_result_identifier(payload),
        check_id=check.check_id,
        status=status,
        message=(
            "Acceptance criteria are defined."
            if passed
            else "Acceptance criteria are missing or empty."
        ),
        evidence={
            "path": path.as_posix(),
            "item_count": str(len(actionable_lines)),
        },
    )