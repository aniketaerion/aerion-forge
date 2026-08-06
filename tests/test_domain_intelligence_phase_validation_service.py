from pathlib import Path

from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationRequest,
)
from forge.domain_intelligence.phase_validation.service import (
    PhaseValidationService,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
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
    (path / "ACCEPTANCE_CRITERIA.md").write_text(
        "# Acceptance\n\n- Architecture exists.\n",
        encoding="utf-8",
    )


def test_phase_validation_service(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = PhaseValidationService().validate(
        PhaseValidationRequest(
            repository_root=str(tmp_path),
            phase="4",
        )
    )

    assert len(report.checks) == 2
    assert len(report.results) == 2
    assert report.passed