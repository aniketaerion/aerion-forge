from pathlib import Path

from forge.autonomous_execution.models import (
    StepExecutionRecord,
    utc_now,
)
from forge.autonomous_execution.reporting import (
    execution_summary,
    render_execution_markdown,
    write_execution_report,
)
from forge.autonomous_execution.states import StepExecutionState


def record() -> StepExecutionRecord:
    return StepExecutionRecord(
        execution_id="execution-1",
        mission_id="mission-1",
        step_id="step-1",
        state=StepExecutionState.SUCCEEDED,
        evidence_ids=("evidence-1",),
        completed_at=utc_now(),
    )


def test_execution_summary_is_structured() -> None:
    summary = execution_summary(record())

    assert summary["execution_id"] == "execution-1"
    assert summary["state"] == "succeeded"
    assert summary["evidence_count"] == 1


def test_execution_markdown_contains_state() -> None:
    report = render_execution_markdown(record())

    assert "Autonomous Execution" in report
    assert "`succeeded`" in report


def test_write_execution_report(tmp_path: Path) -> None:
    json_path, markdown_path = write_execution_report(
        record(),
        tmp_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()