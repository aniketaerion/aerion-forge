"""Execution evidence creation."""

from __future__ import annotations

from forge.autonomous_execution.identifiers import (
    execution_evidence_identifier,
)
from forge.autonomous_execution.models import ExecutionEvidence
from forge.autonomous_execution.tool_contracts import ToolExecutionResult


def build_execution_evidence(
    *,
    execution_id: str,
    result: ToolExecutionResult,
    repository_fingerprint: str,
) -> ExecutionEvidence:
    """Create deterministic evidence from a tool result."""
    payload = {
        "execution_id": execution_id,
        "invocation_id": result.invocation_id,
        "status": result.status.value,
        "result_digest": result.result_digest,
        "repository_fingerprint": repository_fingerprint,
    }

    return ExecutionEvidence(
        evidence_id=execution_evidence_identifier(payload),
        execution_id=execution_id,
        invocation_id=result.invocation_id,
        evidence_kind="tool_execution",
        summary=f"Tool execution ended with {result.status.value}.",
        artifact_references=tuple(
            item
            for item in (
                result.stdout_reference,
                result.stderr_reference,
            )
            if item is not None
        ),
        repository_fingerprint=repository_fingerprint,
    )