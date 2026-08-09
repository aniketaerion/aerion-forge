from forge.general_engineering.execution_evidence import summarize_execution_report
from forge.safe_code_editing.models import FileEditResult, SafeEditReport


def test_execution_report_summary_preserves_fingerprints() -> None:
    report = SafeEditReport(
        request_id="request-1",
        transaction_id="transaction-1",
        dry_run=False,
        approved=True,
        file_results=(
            FileEditResult(
                relative_path="src/service.py",
                original_fingerprint="before",
                resulting_fingerprint="after",
                unified_diff="",
                changed=True,
            ),
        ),
    )

    evidence = summarize_execution_report(report)

    assert evidence[0].path == "src/service.py"
    assert evidence[0].original_fingerprint == "before"
    assert evidence[0].resulting_fingerprint == "after"