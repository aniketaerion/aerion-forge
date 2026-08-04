from forge.validation_repair.models import (
    FindingSeverity,
    ValidationFinding,
    ValidationTool,
)
from forge.validation_repair.planner import plan_repairs


def finding(path: str, finding_id: str) -> ValidationFinding:
    return ValidationFinding(
        finding_id=finding_id,
        tool=ValidationTool.RUFF,
        severity=FindingSeverity.ERROR,
        code="F401",
        message="unused import",
        path=path,
        line=1,
        column=1,
    )


def test_planner_groups_findings_by_path() -> None:
    candidates = plan_repairs(
        (finding("a.py", "f1"), finding("a.py", "f2"), finding("b.py", "f3"))
    )
    assert len(candidates) == 2
    assert candidates[0].target_paths == ("a.py",)
    assert candidates[0].finding_ids == ("f1", "f2")


def test_planner_ignores_findings_without_paths() -> None:
    item = ValidationFinding(
        finding_id="f1",
        tool=ValidationTool.PYTEST,
        severity=FindingSeverity.ERROR,
        code="pytest-failure",
        message="failure",
    )
    assert plan_repairs((item,)) == ()