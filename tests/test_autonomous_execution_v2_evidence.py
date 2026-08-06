from forge.autonomous_execution_v2.attempts import (
    create_attempt,
)
from forge.autonomous_execution_v2.evidence import (
    evidence_from_tool_result,
)
from forge.autonomous_execution_v2.states import EvidenceKind
from forge.autonomous_execution_v2.tool_adapter import (
    ControlledToolResult,
)


def test_tool_result_creates_evidence() -> None:
    evidence = evidence_from_tool_result(
        run_id="run-1",
        step_id="step-1",
        attempt=create_attempt(
            run_id="run-1",
            step_id="step-1",
            attempt_number=1,
        ),
        result=ControlledToolResult(
            invocation_id="invocation-1",
            succeeded=True,
            output_references=("result-1",),
            summary="Tool succeeded.",
        ),
    )

    assert evidence.kind is EvidenceKind.TOOL_RESULT
    assert evidence.references == ("result-1",)