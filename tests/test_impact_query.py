"""Impact Decision query tests."""

import pytest

from forge.impact.builder import ImpactAssessmentBuilder
from forge.impact.errors import ImpactDecisionNotFoundError
from forge.impact.identifiers import build_generation_id
from forge.impact.models import (
    DecisionStatus,
    ImpactAssessment,
    ImpactDecisionGeneration,
    ImpactDecisionStore,
    ImpactSeverity,
)
from forge.impact.query import ImpactQuery
from forge.planning.models import (
    MissionRiskLevel,
    MissionWorkstream,
)
from forge.tasks.decomposer import decompose_mission
from tests.test_task_decomposition import _mission


def _assessment(
    risk: MissionRiskLevel,
    suffix: str,
) -> ImpactAssessment:
    mission = _mission(
        workstreams=(
            MissionWorkstream(
                workstream_id=f"workstream-{suffix}",
                name=f"Implement {suffix}",
                objective=f"Implement {suffix}.",
                expected_outputs=(suffix,),
                risk_level=risk,
            ),
        )
    ).model_copy(
        update={
            "mission_id": f"mission-{suffix}",
            "mission_fingerprint": suffix[0] * 64,
        }
    )
    task_set = decompose_mission(mission)

    return ImpactAssessmentBuilder().build(
        mission,
        task_set,
    )


def _store() -> ImpactDecisionStore:
    low = _assessment(
        MissionRiskLevel.LOW,
        "alpha",
    )
    high = _assessment(
        MissionRiskLevel.HIGH,
        "bravo",
    )

    generations = {}

    for assessment in (low, high):
        generation_id = build_generation_id(
            assessment_id=assessment.assessment_id,
            assessment_fingerprint=(assessment.assessment_fingerprint),
        )
        generations[assessment.assessment_id] = ImpactDecisionGeneration(
            generation_id=generation_id,
            assessment_id=assessment.assessment_id,
            assessment_fingerprint=(assessment.assessment_fingerprint),
            mission_id=assessment.mission_id,
            task_set_fingerprint=(assessment.task_set_fingerprint),
            finding_count=len(assessment.findings),
        )

    return ImpactDecisionStore(
        assessments={
            low.assessment_id: low,
            high.assessment_id: high,
        },
        generations=generations,
    )


def test_list_assessments_is_deterministic() -> None:
    query = ImpactQuery(_store())

    assessments = query.list_assessments()

    assert [assessment.assessment_id for assessment in assessments] == sorted(
        assessment.assessment_id for assessment in assessments
    )


def test_get_assessment() -> None:
    store = _store()
    query = ImpactQuery(store)
    assessment_id = next(iter(store.assessments))

    assert query.get_assessment(assessment_id) == store.assessments[assessment_id]


def test_unknown_assessment_is_rejected() -> None:
    with pytest.raises(ImpactDecisionNotFoundError):
        ImpactQuery(_store()).get_assessment("impact-missing")


def test_filter_by_mission() -> None:
    store = _store()
    query = ImpactQuery(store)
    mission_id = next(iter(store.assessments.values())).mission_id

    result = query.list_by_mission(mission_id)

    assert result
    assert all(assessment.mission_id == mission_id for assessment in result)


def test_filter_by_status() -> None:
    query = ImpactQuery(_store())

    result = query.list_by_status(DecisionStatus.APPROVAL_REQUIRED)

    assert len(result) == 1
    assert result[0].status is DecisionStatus.APPROVAL_REQUIRED


def test_filter_by_severity() -> None:
    query = ImpactQuery(_store())

    result = query.list_by_severity(ImpactSeverity.LOW)

    assert len(result) == 1
    assert result[0].overall_severity is ImpactSeverity.LOW


def test_list_requiring_approval() -> None:
    result = ImpactQuery(_store()).list_requiring_approval()

    assert len(result) == 1


def test_generation_query() -> None:
    store = _store()
    query = ImpactQuery(store)
    assessment_id = next(iter(store.assessments))

    generation = query.get_generation(assessment_id)

    assert generation.assessment_id == assessment_id


def test_unknown_generation_is_rejected() -> None:
    with pytest.raises(ImpactDecisionNotFoundError):
        ImpactQuery(_store()).get_generation("impact-missing")


def test_history_defaults_to_empty() -> None:
    store = _store()
    assessment_id = next(iter(store.assessments))

    assert ImpactQuery(store).get_history(assessment_id) == ()


def test_statistics() -> None:
    statistics = ImpactQuery(_store()).statistics()

    assert statistics["total"] == 2
    assert statistics["approval_required"] == 1
    assert statistics["high"] == 1


def test_query_uses_deep_copy() -> None:
    store = _store()
    query = ImpactQuery(store)

    store.assessments.clear()

    assert len(query.list_assessments()) == 2
