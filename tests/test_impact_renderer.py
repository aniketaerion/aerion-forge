"""Impact Decision renderer tests."""

import json
from pathlib import Path

import pytest

from forge.impact.builder import ImpactAssessmentBuilder
from forge.impact.errors import ImpactReportError
from forge.impact.identifiers import build_generation_id
from forge.impact.models import (
    ImpactAssessment,
    ImpactDecisionGeneration,
)
from forge.impact.renderer import ImpactRenderer
from forge.planning.models import MissionWorkstream
from forge.tasks.decomposer import decompose_mission
from tests.test_task_decomposition import _mission


def _assessment() -> ImpactAssessment:
    mission = _mission(
        workstreams=(
            MissionWorkstream(
                workstream_id="workstream-renderer",
                name="Build Renderer",
                objective="Build the deterministic renderer.",
                expected_outputs=("Reports",),
            ),
        )
    )
    task_set = decompose_mission(mission)

    return ImpactAssessmentBuilder().build(
        mission,
        task_set,
    )


def _generation(
    assessment: ImpactAssessment,
) -> ImpactDecisionGeneration:
    return ImpactDecisionGeneration(
        generation_id=build_generation_id(
            assessment_id=assessment.assessment_id,
            assessment_fingerprint=(assessment.assessment_fingerprint),
        ),
        assessment_id=assessment.assessment_id,
        assessment_fingerprint=(assessment.assessment_fingerprint),
        mission_id=assessment.mission_id,
        task_set_fingerprint=(assessment.task_set_fingerprint),
        finding_count=len(assessment.findings),
    )


def test_render_returns_complete_report_suite() -> None:
    assessment = _assessment()
    renderer = ImpactRenderer()

    reports = renderer.render(
        assessment,
        _generation(assessment),
    )

    assert tuple(reports) == renderer.REPORT_NAMES


def test_json_reports_are_valid() -> None:
    assessment = _assessment()
    reports = ImpactRenderer().render(
        assessment,
        _generation(assessment),
    )

    for name in (
        "IMPACT_ASSESSMENT.json",
        "IMPACT_DECISION.json",
        "IMPACT_EVIDENCE.json",
    ):
        assert isinstance(json.loads(reports[name]), dict)


def test_rendering_is_deterministic() -> None:
    assessment = _assessment()
    generation = _generation(assessment)
    renderer = ImpactRenderer()

    assert renderer.render(
        assessment,
        generation,
    ) == renderer.render(
        assessment,
        generation,
    )


def test_markdown_contains_decision_contract() -> None:
    assessment = _assessment()
    reports = ImpactRenderer().render(
        assessment,
        _generation(assessment),
    )
    markdown = reports["IMPACT_SUMMARY.md"]

    assert assessment.assessment_id in markdown
    assert "## Recommendation" in markdown
    assert "## Safety Boundary" in markdown


def test_write_creates_all_reports(
    tmp_path: Path,
) -> None:
    assessment = _assessment()
    renderer = ImpactRenderer()
    reports = renderer.render(
        assessment,
        _generation(assessment),
    )

    paths = renderer.write(
        tmp_path,
        reports,
    )

    assert len(paths) == len(renderer.REPORT_NAMES)
    assert all(Path(path).is_file() for path in paths)


def test_write_rejects_incomplete_report_set(
    tmp_path: Path,
) -> None:
    with pytest.raises(ImpactReportError):
        ImpactRenderer().write(
            tmp_path,
            {"IMPACT_SUMMARY.md": "incomplete"},
        )


def test_written_reports_are_repeatable(
    tmp_path: Path,
) -> None:
    assessment = _assessment()
    generation = _generation(assessment)
    renderer = ImpactRenderer()
    reports = renderer.render(
        assessment,
        generation,
    )

    renderer.write(tmp_path, reports)
    first = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    renderer.write(tmp_path, reports)
    second = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    assert first == second
