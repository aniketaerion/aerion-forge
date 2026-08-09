from pathlib import Path

from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.validation_planner import build_validation_plan


def test_validation_plan_is_capability_based_and_deterministic(tmp_path: Path) -> None:
    request = build_engineering_request(
        objective="Update service and tests",
        repository_root=tmp_path,
    )
    first = build_validation_plan(request, ("src/service.py", "tests/test_service.py"))
    second = build_validation_plan(request, ("src/service.py", "tests/test_service.py"))

    assert first.validation_plan_id == second.validation_plan_id
    assert first.commands == ()
    assert "repository_tests" in first.capabilities
    assert "focused_tests" in first.capabilities