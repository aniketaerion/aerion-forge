"""Impact Assessment Builder tests."""

from copy import deepcopy

import pytest

from forge.impact.builder import ImpactAssessmentBuilder
from forge.impact.errors import ImpactValidationError
from forge.impact.models import (
    DecisionStatus,
    ImpactSeverity,
)
from forge.impact.validator import validate_assessment
from forge.planning.models import (
    MissionPlan,
    MissionRiskLevel,
    MissionWorkstream,
)
from forge.tasks.decomposer import decompose_mission
from forge.tasks.models import (
    TaskRiskLevel,
    TaskSet,
    TaskStatus,
)
from tests.test_task_decomposition import _mission


def _build(
    risk: MissionRiskLevel = MissionRiskLevel.MEDIUM,
) -> tuple[MissionPlan, TaskSet]:
    mission = _mission(
        workstreams=(
            MissionWorkstream(
                workstream_id="workstream-impact",
                name="Implement Impact Contract",
                objective="Implement the approved impact contract.",
                expected_outputs=("Implementation",),
                risk_level=risk,
            ),
        )
    )
    task_set = decompose_mission(mission)
    return mission, task_set


def test_build_is_deterministic() -> None:
    mission, task_set = _build()
    builder = ImpactAssessmentBuilder()

    first = builder.build(mission, task_set)
    second = builder.build(mission, task_set)

    assert first == second
    assert first.assessment_fingerprint == second.assessment_fingerprint


def test_one_finding_is_created_per_task() -> None:
    mission, task_set = _build()

    assessment = ImpactAssessmentBuilder().build(
        mission,
        task_set,
    )

    assert len(assessment.findings) == len(task_set.tasks)
    assert {finding.affected_task_ids[0] for finding in assessment.findings} == {
        task.task_id for task in task_set.tasks
    }


@pytest.mark.parametrize(
    ("risk", "severity", "status"),
    [
        (
            MissionRiskLevel.LOW,
            ImpactSeverity.LOW,
            DecisionStatus.READY,
        ),
        (
            MissionRiskLevel.MEDIUM,
            ImpactSeverity.MEDIUM,
            DecisionStatus.READY_WITH_CONDITIONS,
        ),
        (
            MissionRiskLevel.HIGH,
            ImpactSeverity.HIGH,
            DecisionStatus.APPROVAL_REQUIRED,
        ),
        (
            MissionRiskLevel.CRITICAL,
            ImpactSeverity.CRITICAL,
            DecisionStatus.APPROVAL_REQUIRED,
        ),
    ],
)
def test_risk_maps_to_severity_and_status(
    risk: MissionRiskLevel,
    severity: ImpactSeverity,
    status: DecisionStatus,
) -> None:
    mission, task_set = _build(risk)

    assessment = ImpactAssessmentBuilder().build(
        mission,
        task_set,
    )

    assert assessment.overall_severity is severity
    assert assessment.status is status


def test_unknown_risk_blocks_assessment() -> None:
    mission, task_set = _build()
    tasks = tuple(
        task.model_copy(update={"risk_level": TaskRiskLevel.UNKNOWN}) for task in task_set.tasks
    )
    changed = task_set.model_copy(update={"tasks": tasks})

    assessment = ImpactAssessmentBuilder().build(
        mission,
        changed,
    )

    assert assessment.status is DecisionStatus.BLOCKED
    assert assessment.blocking_reason is not None


def test_blocked_task_blocks_assessment() -> None:
    mission, task_set = _build()
    first = task_set.tasks[0].model_copy(
        update={
            "status": TaskStatus.BLOCKED,
            "blocking_reason": "Required evidence is missing.",
        }
    )
    changed = task_set.model_copy(
        update={
            "tasks": (first, *task_set.tasks[1:]),
        }
    )

    assessment = ImpactAssessmentBuilder().build(
        mission,
        changed,
    )

    assert assessment.status is DecisionStatus.BLOCKED
    assert assessment.blocking_reason is not None
    assert first.task_id in assessment.blocking_reason


def test_mission_id_mismatch_is_rejected() -> None:
    mission, task_set = _build()
    changed = task_set.model_copy(update={"mission_id": "mission-other"})

    with pytest.raises(ImpactValidationError):
        ImpactAssessmentBuilder().build(
            mission,
            changed,
        )


def test_mission_fingerprint_mismatch_is_rejected() -> None:
    mission, task_set = _build()
    changed = task_set.model_copy(update={"mission_fingerprint": "f" * 64})

    with pytest.raises(ImpactValidationError):
        ImpactAssessmentBuilder().build(
            mission,
            changed,
        )


def test_empty_task_set_is_rejected() -> None:
    mission, task_set = _build()
    changed = task_set.model_copy(update={"tasks": ()})

    with pytest.raises(ImpactValidationError):
        ImpactAssessmentBuilder().build(
            mission,
            changed,
        )


def test_task_from_another_mission_is_rejected() -> None:
    mission, task_set = _build()
    foreign = task_set.tasks[0].model_copy(update={"mission_id": "mission-other"})
    changed = task_set.model_copy(
        update={
            "tasks": (foreign, *task_set.tasks[1:]),
        }
    )

    with pytest.raises(ImpactValidationError):
        ImpactAssessmentBuilder().build(
            mission,
            changed,
        )


def test_builder_does_not_mutate_inputs() -> None:
    mission, task_set = _build()
    mission_before = deepcopy(mission)
    task_set_before = deepcopy(task_set)

    ImpactAssessmentBuilder().build(mission, task_set)

    assert mission == mission_before
    assert task_set == task_set_before


def test_builder_output_passes_validator() -> None:
    mission, task_set = _build(MissionRiskLevel.HIGH)

    assessment = ImpactAssessmentBuilder().build(
        mission,
        task_set,
    )

    assert validate_assessment(assessment).valid


def test_findings_are_canonically_ordered() -> None:
    mission, task_set = _build()

    assessment = ImpactAssessmentBuilder().build(
        mission,
        task_set,
    )

    finding_ids = [finding.finding_id for finding in assessment.findings]
    assert finding_ids == sorted(finding_ids)


def test_recommendation_contains_four_options() -> None:
    mission, task_set = _build()

    assessment = ImpactAssessmentBuilder().build(
        mission,
        task_set,
    )

    assert len(assessment.recommendation.options) == 4
    assert assessment.recommendation.validation_requirements
