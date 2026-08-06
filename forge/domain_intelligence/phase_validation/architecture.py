"""Architecture validation for M4.8 Package 1."""

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


def architecture_check() -> PhaseValidationCheck:
    payload = {
        "name": "Architecture validation",
        "kind": PhaseValidationKind.ARCHITECTURE.value,
    }
    return PhaseValidationCheck(
        check_id=phase_validation_check_identifier(payload),
        name="Architecture validation",
        kind=PhaseValidationKind.ARCHITECTURE,
        description=(
            "Verify that required architecture documents and "
            "implementation packages exist."
        ),
    )


def validate_architecture(
    repository_root: Path,
    phase: str,
) -> PhaseValidationResult:
    check = architecture_check()
    phase_key = phase.lower().replace("phase", "").strip()
    required = (
        repository_root
        / "docs"
        / "domain_intelligence"
        / "phase_validation"
        / "ARCHITECTURE.md"
    )

    exists = required.is_file()
    status = (
        PhaseValidationStatus.PASS
        if exists
        else PhaseValidationStatus.FAIL
    )
    message = (
        f"Phase {phase_key} architecture baseline is available."
        if exists
        else f"Phase {phase_key} architecture baseline is missing."
    )
    payload = {
        "check_id": check.check_id,
        "status": status.value,
        "path": required.as_posix(),
    }

    return PhaseValidationResult(
        result_id=phase_validation_result_identifier(payload),
        check_id=check.check_id,
        status=status,
        message=message,
        evidence={"path": required.as_posix()},
    )