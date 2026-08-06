"""Execution history views."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.models import (
    ExecutionAttempt,
    ExecutionEvidence,
    ExecutionRun,
    RecoveryDecision,
)
from forge.autonomous_execution_v2.repository import InMemoryExecutionRepository


@dataclass(frozen=True, slots=True)
class ExecutionHistory:
    """Complete history for one execution run."""

    run: ExecutionRun
    attempts: tuple[ExecutionAttempt, ...]
    evidence: tuple[ExecutionEvidence, ...]
    recovery_decisions: tuple[RecoveryDecision, ...]


def load_execution_history(
    *,
    repository: InMemoryExecutionRepository,
    run_id: str,
) -> ExecutionHistory | None:
    """Load deterministic execution history."""
    run = repository.get_run(run_id)

    if run is None:
        return None

    return ExecutionHistory(
        run=run,
        attempts=repository.attempts_for_run(run_id),
        evidence=repository.evidence_for_run(run_id),
        recovery_decisions=repository.recovery_for_run(run_id),
    )