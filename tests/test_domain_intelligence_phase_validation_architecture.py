from pathlib import Path

from forge.domain_intelligence.phase_validation.architecture import (
    architecture_check,
    validate_architecture,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationKind,
    PhaseValidationStatus,
)


def test_architecture_check_contract() -> None:
    check = architecture_check()

    assert check.kind is PhaseValidationKind.ARCHITECTURE
    assert check.required


def test_validate_architecture_passes(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "docs"
        / "domain_intelligence"
        / "phase_validation"
    )
    path.mkdir(parents=True)
    (path / "ARCHITECTURE.md").write_text(
        "# Architecture",
        encoding="utf-8",
    )

    result = validate_architecture(tmp_path, "4")

    assert result.status is PhaseValidationStatus.PASS