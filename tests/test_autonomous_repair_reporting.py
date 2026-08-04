import json
from pathlib import Path

from forge.autonomous_repair.models import (
    RepairExecutionAttempt,
    RepairExecutionReport,
    RepairExecutionStatus,
)
from forge.autonomous_repair.reporting import render_markdown, write_report_bundle


def report() -> RepairExecutionReport:
    attempt = RepairExecutionAttempt(
        attempt_number=1,
        proposal_id="proposal-1",
        status=RepairExecutionStatus.DRY_RUN_COMPLETE,
    )
    return RepairExecutionReport(
        session_id="session-1",
        status=RepairExecutionStatus.DRY_RUN_COMPLETE,
        succeeded=False,
        attempts=(attempt,),
        messages=("dry run",),
    )


def test_markdown_contains_session_and_attempt() -> None:
    rendered = render_markdown(report())

    assert "session-1" in rendered
    assert "Attempt 1" in rendered


def test_report_bundle_writes_json_and_markdown(tmp_path: Path) -> None:
    written = write_report_bundle(report(), tmp_path)

    assert set(written) == {
        "AUTONOMOUS_REPAIR_REPORT.md",
        "AUTONOMOUS_REPAIR_SESSION.json",
    }
    payload = json.loads(
        (tmp_path / "AUTONOMOUS_REPAIR_SESSION.json").read_text(encoding="utf-8")
    )
    assert payload["session_id"] == "session-1"