from pathlib import Path

from forge.domain_intelligence.phase_validation.acceptance import (
    validate_acceptance_criteria,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationStatus,
)


def test_validate_acceptance_criteria_passes(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "docs"
        / "domain_intelligence"
        / "phase_validation"
    )
    path.mkdir(parents=True)
    (path / "ACCEPTANCE_CRITERIA.md").write_text(
        "# Acceptance\n\n- Tests pass.\n",
        encoding="utf-8",
    )

    result = validate_acceptance_criteria(tmp_path)

    assert result.status is PhaseValidationStatus.PASS
    assert result.evidence["item_count"] == "1"