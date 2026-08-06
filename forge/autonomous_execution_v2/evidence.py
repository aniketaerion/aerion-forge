"""Evidence capture for M5.7 execution."""

from __future__ import annotations

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.identifiers import (
    execution_evidence_identifier,
)
from forge.autonomous_execution_v2.models import (
    ExecutionAttempt,
    ExecutionEvidence,
)
from forge.autonomous_execution_v2.states import EvidenceKind
from forge.autonomous_execution_v2.tool_adapter import (
    ControlledToolResult,
)


def evidence_from_tool_result(
    *,
    run_id: str,
    step_id: str,
    attempt: ExecutionAttempt,
    result: ControlledToolResult,
) -> ExecutionEvidence:
    """Create evidence from a successful tool result."""
    if not result.succeeded:
        raise ExecutionContractError(
            "Failed tool result cannot produce success evidence."
        )

    if not result.output_references:
        raise ExecutionContractError(
            "Successful tool result requires output references."
        )

    payload = {
        "run_id": run_id,
        "step_id": step_id,
        "attempt_id": attempt.attempt_id,
        "invocation_id": result.invocation_id,
        "references": result.output_references,
    }

    return ExecutionEvidence(
        evidence_id=execution_evidence_identifier(payload),
        run_id=run_id,
        step_id=step_id,
        attempt_id=attempt.attempt_id,
        kind=EvidenceKind.TOOL_RESULT,
        references=result.output_references,
        summary=result.summary or "Controlled tool completed.",
    )