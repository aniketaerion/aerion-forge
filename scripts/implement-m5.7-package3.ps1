[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent

    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$ExpectedBranch = "feature/m5.7-autonomous-execution-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.7 Package 3 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_execution_v2\repository.py" @'
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
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\retry.py" @'
"""Retry policy for M5.7 execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.models import ExecutionAttempt
from forge.autonomous_execution_v2.models import ExecutionAttempt
from forge.autonomous_execution_v2.policies import AutonomousExecutionV2Policy
from forge.autonomous_execution_v2.states import ExecutionAttemptState


@dataclass(frozen=True, slots=True)
class RetryDecision:
    """Deterministic retry decision."""

    allowed: bool
    next_attempt_number: int | None
    rationale: str


def evaluate_retry(
    *,
    attempts: tuple[ExecutionAttempt, ...],
    policy: AutonomousExecutionV2Policy,
) -> RetryDecision:
    """Evaluate whether another attempt is permitted."""
    if not attempts:
        return RetryDecision(
            allowed=True,
            next_attempt_number=1,
            rationale="No prior attempts exist.",
        )

    latest = max(attempts, key=lambda item: item.attempt_number)

    if latest.state is ExecutionAttemptState.SUCCEEDED:
        return RetryDecision(
            allowed=False,
            next_attempt_number=None,
            rationale="Successful step does not require retry.",
        )

    next_number = latest.attempt_number + 1

    if next_number > policy.limits.maximum_attempts_per_step:
        return RetryDecision(
            allowed=False,
            next_attempt_number=None,
            rationale="Maximum step attempts exhausted.",
        )

    return RetryDecision(
        allowed=True,
        next_attempt_number=next_number,
        rationale="Retry permitted by bounded-attempt policy.",
    )
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\recovery.py" @'
"""Recovery decisions for M5.7 autonomous execution."""

from __future__ import annotations

from forge.autonomous_execution_v2.identifiers import deterministic_identifier
from forge.autonomous_execution_v2.models import (
    ExecutionAttempt,
    RecoveryDecision,
)
from forge.autonomous_execution_v2.models import ExecutionAttempt
from forge.autonomous_execution_v2.policies import AutonomousExecutionV2Policy
from forge.autonomous_execution_v2.retry import evaluate_retry
from forge.autonomous_execution_v2.states import RecoveryAction


def decide_recovery(
    *,
    run_id: str,
    step_id: str,
    attempt: ExecutionAttempt,
    attempts_for_step: tuple[ExecutionAttempt, ...],
    policy: AutonomousExecutionV2Policy,
) -> RecoveryDecision:
    """Choose retry or abort after a failed attempt."""
    retry = evaluate_retry(
        attempts=attempts_for_step,
        policy=policy,
    )
    action = RecoveryAction.RETRY if retry.allowed else RecoveryAction.ABORT
    rationale = (
        retry.rationale
        if retry.allowed
        else "Execution cannot safely continue."
    )
    payload = {
        "run_id": run_id,
        "step_id": step_id,
        "attempt_id": attempt.attempt_id,
        "action": action.value,
        "rationale": rationale,
    }

    return RecoveryDecision(
        decision_id=deterministic_identifier(
            "recovery-decision-v2",
            payload,
        ),
        run_id=run_id,
        step_id=step_id,
        attempt_id=attempt.attempt_id,
        action=action,
        rationale=rationale,
    )
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\resume.py" @'
"""Resume controls for paused and recovering runs."""

from __future__ import annotations

from forge.autonomous_execution_v2.errors import ExecutionStateError
from forge.autonomous_execution_v2.models import ExecutionRun
from forge.autonomous_execution_v2.states import ExecutionRunState


def resume_execution_run(run: ExecutionRun) -> ExecutionRun:
    """Resume a paused or recovering execution run."""
    if run.state not in {
        ExecutionRunState.PAUSED,
        ExecutionRunState.RECOVERING,
        ExecutionRunState.AWAITING_APPROVAL,
    }:
        raise ExecutionStateError(
            "Only paused, recovering, or approval-blocked runs can be resumed."
        )

    return run.model_copy(
        update={
            "state": ExecutionRunState.RUNNING,
            "failure_reason": None,
        }
    )
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\history.py" @'
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
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\service.py" @'
"""Application service for M5.7 autonomous execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.authority import ExecutionAuthority
from forge.autonomous_execution_v2.coordinator import (
    AutonomousExecutionCoordinator,
    CoordinatedStepResult,
)
from forge.autonomous_execution_v2.models import ExecutionRun
from forge.autonomous_execution_v2.recovery import decide_recovery
from forge.autonomous_execution_v2.repository import InMemoryExecutionRepository
from forge.autonomous_execution_v2.states import (
    ExecutionRunState,
    RecoveryAction,
)
from forge.autonomous_execution_v2.step_execution import StepToolInvocation


@dataclass(slots=True)
class AutonomousExecutionService:
    """Persisted execution, recovery, and history service."""

    coordinator: AutonomousExecutionCoordinator
    repository: InMemoryExecutionRepository

    def register_run(self, run: ExecutionRun) -> None:
        self.repository.put_run(run)

    def execute_next(
        self,
        *,
        run_id: str,
        invocations_by_step: dict[str, tuple[StepToolInvocation, ...]],
        authority: ExecutionAuthority,
        attempt_number: int = 1,
    ) -> CoordinatedStepResult:
        run = self.repository.get_run(run_id)

        if run is None:
            raise KeyError(f"Unknown execution run: {run_id}")

        result = self.coordinator.execute_next(
            run=run,
            invocations_by_step=invocations_by_step,
            authority=authority,
            attempt_number=attempt_number,
        )
        self.repository.put_run(result.run)
        self.repository.put_attempt(result.outcome.attempt)

        for evidence in result.outcome.evidence:
            self.repository.put_evidence(evidence)

        if not result.outcome.succeeded:
            attempts = tuple(
                attempt
                for attempt in self.repository.attempts_for_run(run_id)
                if attempt.step_id == result.outcome.step_id
            )
            decision = decide_recovery(
                run_id=run_id,
                step_id=result.outcome.step_id,
                attempt=result.outcome.attempt,
                attempts_for_step=attempts,
                policy=self.coordinator.executor.policy,
            )
            self.repository.put_recovery_decision(decision)

            if decision.action is RecoveryAction.RETRY:
                recovering = result.run.model_copy(
                    update={"state": ExecutionRunState.RECOVERING}
                )
                self.repository.put_run(recovering)
                return CoordinatedStepResult(
                    run=recovering,
                    outcome=result.outcome,
                )

        return result
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_repository.py" @'
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.repository import InMemoryExecutionRepository


def test_repository_persists_run() -> None:
    repository = InMemoryExecutionRepository()
    run = ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        steps=(
            ExecutionStep(
                step_id="step-1",
                planning_step_id="planning-step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
            ),
        ),
    )

    repository.put_run(run)

    assert repository.get_run("run-1") == run
    assert repository.all_runs() == (run,)
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_retry.py" @'
from forge.autonomous_execution_v2.attempts import (
    complete_attempt,
    create_attempt,
    start_attempt,
)
from forge.autonomous_execution_v2.models import ExecutionAttempt
from forge.autonomous_execution_v2.policies import AutonomousExecutionV2Policy
from forge.autonomous_execution_v2.retry import evaluate_retry


def failed_attempt(number: int) -> ExecutionAttempt:
    return complete_attempt(
        start_attempt(
            create_attempt(
                run_id="run-1",
                step_id="step-1",
                attempt_number=number,
            )
        ),
        succeeded=False,
        tool_invocation_ids=(),
        failure_reason="Failed.",
    )


def test_retry_is_bounded() -> None:
    policy = AutonomousExecutionV2Policy()
    decision = evaluate_retry(
        attempts=(
            failed_attempt(1),
            failed_attempt(2),
            failed_attempt(3),
        ),
        policy=policy,
    )

    assert not decision.allowed
    assert decision.next_attempt_number is None
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_recovery.py" @'
from forge.autonomous_execution_v2.attempts import (
    complete_attempt,
    create_attempt,
    start_attempt,
)
from forge.autonomous_execution_v2.models import ExecutionAttempt
from forge.autonomous_execution_v2.policies import AutonomousExecutionV2Policy
from forge.autonomous_execution_v2.recovery import decide_recovery
from forge.autonomous_execution_v2.states import RecoveryAction


def test_recovery_requests_retry() -> None:
    attempt = complete_attempt(
        start_attempt(
            create_attempt(
                run_id="run-1",
                step_id="step-1",
                attempt_number=1,
            )
        ),
        succeeded=False,
        tool_invocation_ids=(),
        failure_reason="Failed.",
    )

    decision = decide_recovery(
        run_id="run-1",
        step_id="step-1",
        attempt=attempt,
        attempts_for_step=(attempt,),
        policy=AutonomousExecutionV2Policy(),
    )

    assert decision.action is RecoveryAction.RETRY
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_resume.py" @'
import pytest

from forge.autonomous_execution_v2.errors import ExecutionStateError
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.resume import resume_execution_run
from forge.autonomous_execution_v2.states import ExecutionRunState


def run(state: ExecutionRunState) -> ExecutionRun:
    return ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        state=state,
        steps=(
            ExecutionStep(
                step_id="step-1",
                planning_step_id="planning-step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
            ),
        ),
    )


def test_recovering_run_can_resume() -> None:
    resumed = resume_execution_run(run(ExecutionRunState.RECOVERING))

    assert resumed.state is ExecutionRunState.RUNNING


def test_completed_run_cannot_resume() -> None:
    with pytest.raises(ExecutionStateError):
        resume_execution_run(run(ExecutionRunState.SUCCEEDED))
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_history.py" @'
from forge.autonomous_execution_v2.history import load_execution_history
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.repository import InMemoryExecutionRepository


def test_history_loads_run() -> None:
    repository = InMemoryExecutionRepository()
    run = ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        steps=(
            ExecutionStep(
                step_id="step-1",
                planning_step_id="planning-step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
            ),
        ),
    )
    repository.put_run(run)

    history = load_execution_history(
        repository=repository,
        run_id="run-1",
    )

    assert history is not None
    assert history.run == run
'@

Write-Host ""
Write-Host "M5.7 Package 3 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check forge tests --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check forge tests
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_execution_v2_repository.py `
    .\tests\test_autonomous_execution_v2_retry.py `
    .\tests\test_autonomous_execution_v2_recovery.py `
    .\tests\test_autonomous_execution_v2_resume.py `
    .\tests\test_autonomous_execution_v2_history.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.7 Package 3 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository tests"

Write-Host ""
Write-Host "M5.7 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short