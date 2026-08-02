"""Safe Change Planning renderer tests."""

import json
from pathlib import Path

import pytest

from forge.safe_change_planning.builder import (
    SafeChangePlanningBuilder,
)
from forge.safe_change_planning.errors import (
    ChangePlanningReportError,
)
from forge.safe_change_planning.models import (
    ChangeActionType,
    ChangePlanningConfiguration,
    ChangeTargetType,
    PlanningPhaseType,
    SafeChangePlan,
    VerificationType,
)
from forge.safe_change_planning.renderer import (
    SAFE_CHANGE_PLAN_JSON,
    SAFE_CHANGE_PLAN_MARKDOWN,
    SAFE_CHANGE_REPORT_NAMES,
    SAFE_CHANGE_RISKS_JSON,
    SAFE_CHANGE_ROLLBACK_JSON,
    SAFE_CHANGE_SUMMARY_JSON,
    SAFE_CHANGE_TARGETS_JSON,
    SAFE_CHANGE_TRACEABILITY_JSON,
    SAFE_CHANGE_VERIFICATION_JSON,
    SafeChangePlanningRenderer,
)


def _lineage() -> dict[str, str]:
    return {
        "mission": "1",
        "tasks": "2",
        "impact": "3",
        "engineering_memory": "4",
        "mission_report": "5",
        "repository": "6",
        "index": "7",
        "knowledge_graph": "8",
    }


def _plan() -> SafeChangePlan:
    builder = SafeChangePlanningBuilder()
    request = builder.build_request(
        mission_id="mission-1",
        task_ids=("task-1",),
        objective="Implement safe change",
        source_fingerprints={
            "mission": "1",
            "tasks": "2",
        },
    )
    target = builder.build_target(
        target_type=ChangeTargetType.FILE,
        path="forge/example.py",
        component="example",
        reason="Required implementation",
        source_ids=("task-1",),
    )
    verification = builder.build_verification_step(
        request_id=request.request_id,
        verification_type=VerificationType.UNIT_TEST,
        description="Run unit tests",
        target_ids=(target.target_id,),
        command="python -m pytest",
    )
    rollback = builder.build_rollback_step(
        request_id=request.request_id,
        description="Restore previous version",
        target_ids=(target.target_id,),
    )
    action = builder.build_action(
        request_id=request.request_id,
        target_id=target.target_id,
        action_type=ChangeActionType.MODIFY,
        description="Modify implementation",
        verification_step_ids=(verification.step_id,),
        rollback_step_ids=(rollback.step_id,),
    )
    phase = builder.build_phase(
        request_id=request.request_id,
        phase_type=PlanningPhaseType.IMPLEMENTATION,
        sequence=1,
        title="Implementation",
        action_ids=(action.action_id,),
    )

    return builder.build_plan(
        request=request,
        targets=(target,),
        actions=(action,),
        dependencies=(),
        verification_steps=(verification,),
        rollback_steps=(rollback,),
        phases=(phase,),
        source_fingerprints=_lineage(),
        configuration=ChangePlanningConfiguration(),
    )


def test_render_plan_json_is_valid() -> None:
    payload = json.loads(SafeChangePlanningRenderer().render_plan_json(_plan()))

    assert payload["plan_id"] == _plan().plan_id


def test_render_plan_json_is_deterministic() -> None:
    renderer = SafeChangePlanningRenderer()

    assert renderer.render_plan_json(_plan()) == renderer.render_plan_json(_plan())


def test_render_summary_contains_identity() -> None:
    payload = json.loads(SafeChangePlanningRenderer().render_summary_json(_plan()))

    assert payload["plan_id"] == _plan().plan_id
    assert payload["mission_id"] == "mission-1"


def test_render_summary_contains_statistics() -> None:
    payload = json.loads(SafeChangePlanningRenderer().render_summary_json(_plan()))

    assert payload["statistics"]["target_count"] == 1
    assert payload["statistics"]["action_count"] == 1


def test_render_targets_contains_target() -> None:
    payload = json.loads(SafeChangePlanningRenderer().render_targets_json(_plan()))

    assert len(payload["targets"]) == 1
    assert payload["targets"][0]["path"] == ("forge/example.py")


def test_render_targets_contains_action() -> None:
    payload = json.loads(SafeChangePlanningRenderer().render_targets_json(_plan()))

    assert len(payload["actions"]) == 1


def test_render_risks_contains_assessment() -> None:
    payload = json.loads(SafeChangePlanningRenderer().render_risks_json(_plan()))

    assert "assessment" in payload
    assert "risk_level" in payload["assessment"]


def test_render_verification_contains_command() -> None:
    payload = json.loads(SafeChangePlanningRenderer().render_verification_json(_plan()))

    assert payload["verification_steps"][0]["command"] == "python -m pytest"


def test_render_rollback_contains_step() -> None:
    payload = json.loads(SafeChangePlanningRenderer().render_rollback_json(_plan()))

    assert len(payload["rollback_steps"]) == 1


def test_render_traceability_contains_lineage() -> None:
    payload = json.loads(SafeChangePlanningRenderer().render_traceability_json(_plan()))

    assert payload["plan_source_fingerprints"]["mission"] == "1"


def test_render_markdown_contains_heading() -> None:
    markdown = SafeChangePlanningRenderer().render_markdown(_plan())

    assert "# Safe Change Plan" in markdown


def test_render_markdown_contains_objective() -> None:
    markdown = SafeChangePlanningRenderer().render_markdown(_plan())

    assert "Implement safe change" in markdown


def test_render_markdown_contains_target() -> None:
    markdown = SafeChangePlanningRenderer().render_markdown(_plan())

    assert "forge/example.py" in markdown


def test_render_markdown_contains_verification() -> None:
    markdown = SafeChangePlanningRenderer().render_markdown(_plan())

    assert "Run unit tests" in markdown
    assert "python -m pytest" in markdown


def test_render_markdown_contains_rollback() -> None:
    markdown = SafeChangePlanningRenderer().render_markdown(_plan())

    assert "Restore previous version" in markdown


def test_render_markdown_contains_safety_boundary() -> None:
    markdown = SafeChangePlanningRenderer().render_markdown(_plan())

    assert "does not modify source code" in markdown


def test_render_suite_has_exact_files() -> None:
    suite = SafeChangePlanningRenderer().render_suite(_plan())

    assert set(suite) == set(SAFE_CHANGE_REPORT_NAMES)


def test_render_suite_includes_declared_names() -> None:
    suite = SafeChangePlanningRenderer().render_suite(_plan())

    assert SAFE_CHANGE_PLAN_JSON in suite
    assert SAFE_CHANGE_SUMMARY_JSON in suite
    assert SAFE_CHANGE_TARGETS_JSON in suite
    assert SAFE_CHANGE_RISKS_JSON in suite
    assert SAFE_CHANGE_VERIFICATION_JSON in suite
    assert SAFE_CHANGE_ROLLBACK_JSON in suite
    assert SAFE_CHANGE_TRACEABILITY_JSON in suite
    assert SAFE_CHANGE_PLAN_MARKDOWN in suite


def test_write_suite_creates_all_files(
    tmp_path: Path,
) -> None:
    written = SafeChangePlanningRenderer().write_suite(
        _plan(),
        tmp_path,
    )

    assert set(written) == set(SAFE_CHANGE_REPORT_NAMES)

    for name in SAFE_CHANGE_REPORT_NAMES:
        assert (tmp_path / name).is_file()


def test_written_files_match_rendered_suite(
    tmp_path: Path,
) -> None:
    renderer = SafeChangePlanningRenderer()
    plan = _plan()
    expected = renderer.render_suite(plan)

    renderer.write_suite(plan, tmp_path)

    for name, content in expected.items():
        assert (tmp_path / name).read_text(encoding="utf-8") == content


def test_write_suite_overwrites_existing_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / SAFE_CHANGE_PLAN_JSON
    path.write_text("old", encoding="utf-8")

    SafeChangePlanningRenderer().write_suite(
        _plan(),
        tmp_path,
    )

    assert path.read_text(encoding="utf-8") != "old"


def test_write_suite_removes_temporary_files(
    tmp_path: Path,
) -> None:
    SafeChangePlanningRenderer().write_suite(
        _plan(),
        tmp_path,
    )

    assert not tuple(tmp_path.glob("*.tmp"))


def test_write_suite_wraps_directory_failure(
    tmp_path: Path,
) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("file", encoding="utf-8")

    with pytest.raises(ChangePlanningReportError):
        SafeChangePlanningRenderer().write_suite(
            _plan(),
            blocked,
        )


def test_json_reports_end_with_newline() -> None:
    suite = SafeChangePlanningRenderer().render_suite(_plan())

    for name, content in suite.items():
        if name.endswith(".json"):
            assert content.endswith("\n")
