from pathlib import Path

import pytest

from forge.general_engineering.models import RelevantFile
from forge.general_engineering.planning_policy import select_planning_targets
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.states import EngineeringRisk


def _relevant(path: str) -> RelevantFile:
    return RelevantFile(
        path=path,
        evidence_ids=(f"evidence-{path}",),
        rationale="repository evidence",
    )


def test_explicit_targets_must_be_grounded(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update service",
        repository_root=tmp_path,
        explicit_target_paths=("src/missing.py",),
    )
    with pytest.raises(ValueError, match="not repository-grounded"):
        select_planning_targets(request, (_relevant("src/service.py"),))


def test_small_plan_is_low_aggregate_risk(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update service",
        repository_root=tmp_path,
    )
    decision = select_planning_targets(
        request,
        (_relevant("src/service.py"), _relevant("tests/test_service.py")),
    )
    assert decision.aggregate_risk is EngineeringRisk.LOW