from forge.autonomous_execution.evidence import (
    build_execution_evidence,
)
from forge.autonomous_execution.states import ToolExecutionStatus
from forge.autonomous_execution.tool_contracts import ToolExecutionResult


def test_evidence_is_built_from_tool_result() -> None:
    result = ToolExecutionResult(
        invocation_id="invocation-1",
        status=ToolExecutionStatus.SUCCEEDED,
        exit_code=0,
        result_digest="digest-1",
        started_at="2026-08-06T00:00:00+00:00",
        completed_at="2026-08-06T00:00:01+00:00",
    )

    evidence = build_execution_evidence(
        execution_id="execution-1",
        result=result,
        repository_fingerprint="fingerprint-1",
    )

    assert evidence.invocation_id == "invocation-1"
    assert evidence.repository_fingerprint == "fingerprint-1"