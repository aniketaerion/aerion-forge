"""Persistence repository for M5.7 autonomous execution."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_execution_v2.errors import ExecutionContractError
from forge.autonomous_execution_v2.models import (
    ExecutionAttempt,
    ExecutionEvidence,
    ExecutionRequest,
    ExecutionRun,
    RecoveryDecision,
)


@dataclass(slots=True)
class InMemoryExecutionRepository:
    """Deterministic in-memory execution repository."""

    _requests: dict[str, ExecutionRequest] = field(default_factory=dict)
    _runs: dict[str, ExecutionRun] = field(default_factory=dict)
    _attempts: dict[str, ExecutionAttempt] = field(default_factory=dict)
    _evidence: dict[str, ExecutionEvidence] = field(default_factory=dict)
    _recovery_decisions: dict[str, RecoveryDecision] = field(default_factory=dict)

    def put_request(self, request: ExecutionRequest) -> None:
        existing = self._requests.get(request.request_id)

        if existing is not None and existing != request:
            raise ExecutionContractError(
                f"Conflicting execution request: {request.request_id}"
            )

        self._requests[request.request_id] = request

    def get_request(self, request_id: str) -> ExecutionRequest | None:
        return self._requests.get(request_id)

    def put_run(self, run: ExecutionRun) -> None:
        self._runs[run.run_id] = run

    def get_run(self, run_id: str) -> ExecutionRun | None:
        return self._runs.get(run_id)

    def put_attempt(self, attempt: ExecutionAttempt) -> None:
        self._attempts[attempt.attempt_id] = attempt

    def attempts_for_run(self, run_id: str) -> tuple[ExecutionAttempt, ...]:
        return tuple(
            sorted(
                (
                    attempt
                    for attempt in self._attempts.values()
                    if attempt.run_id == run_id
                ),
                key=lambda item: (
                    item.step_id,
                    item.attempt_number,
                    item.attempt_id,
                ),
            )
        )

    def put_evidence(self, evidence: ExecutionEvidence) -> None:
        self._evidence[evidence.evidence_id] = evidence

    def evidence_for_run(self, run_id: str) -> tuple[ExecutionEvidence, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self._evidence.values()
                    if item.run_id == run_id
                ),
                key=lambda item: (
                    item.step_id,
                    item.attempt_id,
                    item.evidence_id,
                ),
            )
        )

    def put_recovery_decision(self, decision: RecoveryDecision) -> None:
        self._recovery_decisions[decision.decision_id] = decision

    def recovery_for_run(self, run_id: str) -> tuple[RecoveryDecision, ...]:
        return tuple(
            sorted(
                (
                    item
                    for item in self._recovery_decisions.values()
                    if item.run_id == run_id
                ),
                key=lambda item: (
                    item.created_at,
                    item.decision_id,
                ),
            )
        )

    def all_runs(self) -> tuple[ExecutionRun, ...]:
        return tuple(self._runs[key] for key in sorted(self._runs))