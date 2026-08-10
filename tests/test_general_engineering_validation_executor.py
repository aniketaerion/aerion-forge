from pathlib import Path

from forge.general_engineering.models import (
    ChangePlan,
    ChangeRequirement,
    FileChangePlan,
    ValidationPlan,
)
from forge.general_engineering.request_builder import build_engineering_request
from forge.general_engineering.states import EditOperationType, EngineeringRisk, ValidationStatus
from forge.general_engineering.validation_executor import (
    CommandResult,
    EngineeringValidationExecutor,
)


def _plan(request_id: str) -> ChangePlan:
    requirement = ChangeRequirement(requirement_id="r1", description="change")
    return ChangePlan(
        plan_id="p1",
        request_id=request_id,
        objective="change",
        requirements=(requirement,),
        file_changes=(
            FileChangePlan(
                path="src/service.py",
                rationale="grounded",
                evidence_ids=("e1",),
                intended_operations=(EditOperationType.REPLACE,),
                expected_effect="change",
            ),
        ),
        validation_plan=ValidationPlan(
            validation_plan_id="v1",
            capabilities=("repository_tests",),
        ),
        expected_effect="change",
        aggregate_risk=EngineeringRisk.LOW,
        evidence_ids=("e1",),
    )


def test_validation_executor_records_failure(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    request = build_engineering_request(objective="change", repository_root=tmp_path)

    def runner(argv: tuple[str, ...], cwd: Path, timeout: int) -> CommandResult:
        assert cwd == tmp_path.resolve()
        assert timeout == 30
        return CommandResult(returncode=1, stdout="failed", stderr="")

    outcome = EngineeringValidationExecutor(runner=runner, timeout_seconds=30).validate(
        request=request,
        plan=_plan(request.request_id),
    )
    assert outcome.status is ValidationStatus.FAILED
    assert outcome.failures
