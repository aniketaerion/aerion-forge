"""Impact Decision persistence tests."""

import json
from pathlib import Path

import pytest

from forge.impact.builder import ImpactAssessmentBuilder
from forge.impact.errors import (
    ImpactPersistenceError,
    ImpactSchemaMismatchError,
    ImpactStoreCorruptionError,
)
from forge.impact.identifiers import build_generation_id
from forge.impact.models import (
    ImpactAssessment,
    ImpactDecisionGeneration,
)
from forge.impact.store import ImpactRepository
from forge.planning.models import (
    MissionRiskLevel,
    MissionWorkstream,
)
from forge.tasks.decomposer import decompose_mission
from tests.test_task_decomposition import _mission


def _assessment(
    risk: MissionRiskLevel = MissionRiskLevel.MEDIUM,
) -> ImpactAssessment:
    mission = _mission(
        workstreams=(
            MissionWorkstream(
                workstream_id="workstream-store",
                name="Implement Store Contract",
                objective="Implement the approved store contract.",
                expected_outputs=("Store",),
                risk_level=risk,
            ),
        )
    )
    task_set = decompose_mission(mission)
    assessment = ImpactAssessmentBuilder().build(
        mission,
        task_set,
    )
    return assessment


def _generation(
    assessment: ImpactAssessment,
) -> ImpactDecisionGeneration:
    generation_id = build_generation_id(
        assessment_id=assessment.assessment_id,
        assessment_fingerprint=(assessment.assessment_fingerprint),
    )

    return ImpactDecisionGeneration(
        generation_id=generation_id,
        assessment_id=assessment.assessment_id,
        assessment_fingerprint=(assessment.assessment_fingerprint),
        mission_id=assessment.mission_id,
        task_set_fingerprint=(assessment.task_set_fingerprint),
        finding_count=len(assessment.findings),
    )


def test_missing_store_returns_empty_store(
    tmp_path: Path,
) -> None:
    repository = ImpactRepository(tmp_path / "impact.json")

    store = repository.load()

    assert store.assessments == {}
    assert store.history == {}
    assert store.generations == {}


def test_save_and_load_assessment(
    tmp_path: Path,
) -> None:
    repository = ImpactRepository(tmp_path / "impact.json")
    assessment = _assessment()

    repository.save(
        assessment,
        _generation(assessment),
    )

    loaded = repository.load()

    assert loaded.assessments[assessment.assessment_id] == assessment


def test_identical_save_does_not_add_history(
    tmp_path: Path,
) -> None:
    repository = ImpactRepository(tmp_path / "impact.json")
    assessment = _assessment()
    generation = _generation(assessment)

    repository.save(assessment, generation)
    repository.save(assessment, generation)

    assert repository.load().history == {}


def test_changed_assessment_adds_history(
    tmp_path: Path,
) -> None:
    repository = ImpactRepository(tmp_path / "impact.json")
    first = _assessment(MissionRiskLevel.LOW)
    second = first.model_copy(
        update={
            "assessment_fingerprint": "f" * 64,
        }
    )
    generation = _generation(second)

    repository.save(
        first,
        _generation(first),
    )
    repository.save(second, generation)

    history = repository.load().history[first.assessment_id]

    assert history == [first]


def test_history_is_bounded(
    tmp_path: Path,
) -> None:
    repository = ImpactRepository(
        tmp_path / "impact.json",
        history_limit=1,
    )
    original = _assessment()

    repository.save(
        original,
        _generation(original),
    )

    second = original.model_copy(update={"assessment_fingerprint": "b" * 64})
    repository.save(
        second,
        _generation(second),
    )

    third = original.model_copy(update={"assessment_fingerprint": "c" * 64})
    repository.save(
        third,
        _generation(third),
    )

    history = repository.load().history[original.assessment_id]

    assert history == [second]


def test_delete_removes_active_assessment(
    tmp_path: Path,
) -> None:
    repository = ImpactRepository(tmp_path / "impact.json")
    assessment = _assessment()

    repository.save(
        assessment,
        _generation(assessment),
    )
    store = repository.delete(assessment.assessment_id)

    assert assessment.assessment_id not in store.assessments
    assert assessment.assessment_id not in store.generations


def test_snapshot_and_restore(
    tmp_path: Path,
) -> None:
    repository = ImpactRepository(tmp_path / "impact.json")
    assessment = _assessment()

    repository.save(
        assessment,
        _generation(assessment),
    )
    snapshot = repository.snapshot_bytes()

    repository.delete(assessment.assessment_id)
    repository.restore_bytes(snapshot)

    assert repository.load().assessments[assessment.assessment_id] == assessment


def test_restore_none_removes_store(
    tmp_path: Path,
) -> None:
    repository = ImpactRepository(tmp_path / "impact.json")
    assessment = _assessment()

    repository.save(
        assessment,
        _generation(assessment),
    )
    repository.restore_bytes(None)

    assert not repository.path.exists()


def test_corrupt_json_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "impact.json"
    path.write_text("{invalid", encoding="utf-8")

    with pytest.raises(ImpactStoreCorruptionError):
        ImpactRepository(path).load()


def test_non_object_json_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "impact.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ImpactStoreCorruptionError):
        ImpactRepository(path).load()


def test_schema_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    path = tmp_path / "impact.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": "999",
                "assessments": {},
                "history": {},
                "generations": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ImpactSchemaMismatchError):
        ImpactRepository(path).load()


def test_generation_mismatch_is_rejected(
    tmp_path: Path,
) -> None:
    repository = ImpactRepository(tmp_path / "impact.json")
    assessment = _assessment()
    generation = _generation(assessment).model_copy(update={"mission_id": "mission-other"})

    with pytest.raises(ImpactPersistenceError):
        repository.save(
            assessment,
            generation,
        )


def test_probe_write_leaves_no_files(
    tmp_path: Path,
) -> None:
    repository = ImpactRepository(tmp_path / "memory" / "impact.json")

    repository.probe_write()

    assert list((tmp_path / "memory").iterdir()) == []


def test_serialized_store_is_deterministic(
    tmp_path: Path,
) -> None:
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    assessment = _assessment()
    generation = _generation(assessment)

    ImpactRepository(first_path).save(
        assessment,
        generation,
    )
    ImpactRepository(second_path).save(
        assessment,
        generation,
    )

    assert first_path.read_bytes() == second_path.read_bytes()
