from pathlib import Path

from forge.autonomous_decision.cli import sample_decision_result
from forge.autonomous_decision.reporting import (
    decision_summary,
    render_decision_markdown,
    write_decision_report,
)


def test_decision_summary_is_structured() -> None:
    summary = decision_summary(sample_decision_result())

    assert summary["decision_id"]
    assert summary["disposition"] == "select_action"
    assert summary["selected_candidate_id"] is not None
    assert summary["ranked_candidates"]


def test_no_safe_action_report_contains_stop() -> None:
    result = sample_decision_result(with_evidence=False)
    summary = decision_summary(result)
    report = render_decision_markdown(result)

    assert summary["disposition"] == "no_safe_action"
    assert summary["stop"] is not None
    assert "Stop Decision" in report


def test_write_decision_report(tmp_path: Path) -> None:
    json_path, markdown_path = write_decision_report(
        sample_decision_result(),
        tmp_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()
    assert "select_action" in json_path.read_text(
        encoding="utf-8"
    )