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

    New-Item `
        -ItemType Directory `
        -Path $Directory `
        -Force | Out-Null

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
    throw "M5.7 Package 2 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_execution_v2\authority.py" @'
"""Authority checks for M5.7 controlled execution."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.errors import (
    ExecutionAuthorityError,
    ExecutionPolicyError,
)
from forge.autonomous_execution_v2.models import ExecutionStep
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)


@dataclass(frozen=True, slots=True)
class ExecutionAuthority:
    """Authority granted to one execution run."""

    subject: str
    repository_root: str
    permitted_tools: tuple[str, ...] = ()
    permitted_capabilities: tuple[str, ...] = ()
    high_risk_approved: bool = False
    destructive_approved: bool = False


def assert_step_authorized(
    *,
    step: ExecutionStep,
    authority: ExecutionAuthority,
    policy: AutonomousExecutionV2Policy,
) -> None:
    """Raise when a step is outside the granted authority."""
    if not authority.subject.strip():
        raise ExecutionAuthorityError(
            "Execution authority subject cannot be empty."
        )

    missing_tools = tuple(
        tool
        for tool in step.required_tools
        if tool not in authority.permitted_tools
    )

    if missing_tools:
        raise ExecutionAuthorityError(
            "Execution authority does not permit tools: "
            + ", ".join(missing_tools)
        )

    if (
        step.risk in {"high", "critical"}
        and policy.safety.require_approval_for_high_risk
        and not authority.high_risk_approved
    ):
        raise ExecutionAuthorityError(
            "High-risk execution requires explicit approval."
        )

    if step.destructive:
        if not policy.safety.allow_destructive_execution:
            raise ExecutionPolicyError(
                "Destructive execution is forbidden by policy."
            )

        if not authority.destructive_approved:
            raise ExecutionAuthorityError(
                "Destructive execution requires explicit approval."
            )
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\tool_adapter.py" @'
"""Controlled tool-gateway adapter contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ControlledToolRequest:
    """One controlled tool invocation request."""

    invocation_id: str
    run_id: str
    step_id: str
    tool_name: str
    arguments: dict[str, object]


@dataclass(frozen=True, slots=True)
class ControlledToolResult:
    """Normalized result returned by the controlled gateway."""

    invocation_id: str
    succeeded: bool
    output_references: tuple[str, ...] = ()
    summary: str = ""
    error: str | None = None


class ControlledToolGateway(Protocol):
    """Protocol implemented by the M5.2 controlled gateway adapter."""

    def execute(
        self,
        request: ControlledToolRequest,
    ) -> ControlledToolResult:
        """Execute one governed tool request."""
        ...
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\attempts.py" @'
"""Execution-attempt lifecycle management."""

from __future__ import annotations

from datetime import datetime, timezone

from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
    ExecutionStateError,
)
from forge.autonomous_execution_v2.identifiers import (
    execution_attempt_identifier,
)
from forge.autonomous_execution_v2.models import ExecutionAttempt
from forge.autonomous_execution_v2.states import (
    ExecutionAttemptState,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_attempt(
    *,
    run_id: str,
    step_id: str,
    attempt_number: int,
) -> ExecutionAttempt:
    """Create a deterministic execution attempt."""
    if attempt_number < 1:
        raise ExecutionContractError(
            "Attempt number must be positive."
        )

    payload = {
        "run_id": run_id,
        "step_id": step_id,
        "attempt_number": attempt_number,
    }

    return ExecutionAttempt(
        attempt_id=execution_attempt_identifier(payload),
        run_id=run_id,
        step_id=step_id,
        attempt_number=attempt_number,
    )


def start_attempt(
    attempt: ExecutionAttempt,
) -> ExecutionAttempt:
    """Move an attempt from created to running."""
    if attempt.state is not ExecutionAttemptState.CREATED:
        raise ExecutionStateError(
            "Only created attempts can be started."
        )

    return attempt.model_copy(
        update={
            "state": ExecutionAttemptState.RUNNING,
            "started_at": utc_now(),
        }
    )


def complete_attempt(
    attempt: ExecutionAttempt,
    *,
    succeeded: bool,
    tool_invocation_ids: tuple[str, ...],
    failure_reason: str | None = None,
) -> ExecutionAttempt:
    """Complete a running execution attempt."""
    if attempt.state is not ExecutionAttemptState.RUNNING:
        raise ExecutionStateError(
            "Only running attempts can be completed."
        )

    if not succeeded and not failure_reason:
        raise ExecutionContractError(
            "Failed attempt requires a failure reason."
        )

    return attempt.model_copy(
        update={
            "state": (
                ExecutionAttemptState.SUCCEEDED
                if succeeded
                else ExecutionAttemptState.FAILED
            ),
            "tool_invocation_ids": tool_invocation_ids,
            "failure_reason": failure_reason,
            "completed_at": utc_now(),
        }
    )
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\evidence.py" @'
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
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\step_execution.py" @'
"""Controlled execution of one M5.7 step."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.attempts import (
    complete_attempt,
    create_attempt,
    start_attempt,
)
from forge.autonomous_execution_v2.authority import (
    ExecutionAuthority,
    assert_step_authorized,
)
from forge.autonomous_execution_v2.evidence import (
    evidence_from_tool_result,
)
from forge.autonomous_execution_v2.models import (
    ExecutionAttempt,
    ExecutionEvidence,
    ExecutionStep,
)
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)
from forge.autonomous_execution_v2.tool_adapter import (
    ControlledToolGateway,
    ControlledToolRequest,
    ControlledToolResult,
)


@dataclass(frozen=True, slots=True)
class StepToolInvocation:
    """Planned controlled invocation for one execution step."""

    invocation_id: str
    tool_name: str
    arguments: dict[str, object]


@dataclass(frozen=True, slots=True)
class StepExecutionOutcome:
    """Result of executing one step attempt."""

    step_id: str
    attempt: ExecutionAttempt
    tool_results: tuple[ControlledToolResult, ...]
    evidence: tuple[ExecutionEvidence, ...]

    @property
    def succeeded(self) -> bool:
        return self.attempt.state.value == "succeeded"


@dataclass(frozen=True, slots=True)
class ControlledStepExecutor:
    """Execute step invocations exclusively through a gateway."""

    gateway: ControlledToolGateway
    policy: AutonomousExecutionV2Policy

    def execute(
        self,
        *,
        run_id: str,
        step: ExecutionStep,
        attempt_number: int,
        invocations: tuple[StepToolInvocation, ...],
        authority: ExecutionAuthority,
    ) -> StepExecutionOutcome:
        assert_step_authorized(
            step=step,
            authority=authority,
            policy=self.policy,
        )
        attempt = start_attempt(
            create_attempt(
                run_id=run_id,
                step_id=step.step_id,
                attempt_number=attempt_number,
            )
        )
        results: list[ControlledToolResult] = []
        evidence: list[ExecutionEvidence] = []

        for invocation in invocations:
            result = self.gateway.execute(
                ControlledToolRequest(
                    invocation_id=invocation.invocation_id,
                    run_id=run_id,
                    step_id=step.step_id,
                    tool_name=invocation.tool_name,
                    arguments=invocation.arguments,
                )
            )
            results.append(result)

            if result.succeeded:
                evidence.append(
                    evidence_from_tool_result(
                        run_id=run_id,
                        step_id=step.step_id,
                        attempt=attempt,
                        result=result,
                    )
                )
            else:
                failed = complete_attempt(
                    attempt,
                    succeeded=False,
                    tool_invocation_ids=tuple(
                        item.invocation_id
                        for item in results
                    ),
                    failure_reason=(
                        result.error
                        or "Controlled tool execution failed."
                    ),
                )
                return StepExecutionOutcome(
                    step_id=step.step_id,
                    attempt=failed,
                    tool_results=tuple(results),
                    evidence=tuple(evidence),
                )

        completed = complete_attempt(
            attempt,
            succeeded=True,
            tool_invocation_ids=tuple(
                item.invocation_id
                for item in results
            ),
        )

        return StepExecutionOutcome(
            step_id=step.step_id,
            attempt=completed,
            tool_results=tuple(results),
            evidence=tuple(evidence),
        )
'@

Write-Utf8NoBom "forge\autonomous_execution_v2\coordinator.py" @'
"""Execution coordination for M5.7."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_execution_v2.authority import (
    ExecutionAuthority,
)
from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
    ExecutionStateError,
)
from forge.autonomous_execution_v2.graph_builder import (
    ExecutionGraphBuilder,
)
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.scheduler import (
    build_execution_schedule,
)
from forge.autonomous_execution_v2.states import (
    ExecutionRunState,
    ExecutionStepState,
)
from forge.autonomous_execution_v2.step_execution import (
    ControlledStepExecutor,
    StepExecutionOutcome,
    StepToolInvocation,
)


@dataclass(frozen=True, slots=True)
class CoordinatedStepResult:
    """Updated run and one step outcome."""

    run: ExecutionRun
    outcome: StepExecutionOutcome


@dataclass(frozen=True, slots=True)
class AutonomousExecutionCoordinator:
    """Select and execute the next eligible step."""

    graph_builder: ExecutionGraphBuilder
    executor: ControlledStepExecutor

    def execute_next(
        self,
        *,
        run: ExecutionRun,
        invocations_by_step: dict[
            str,
            tuple[StepToolInvocation, ...],
        ],
        authority: ExecutionAuthority,
        attempt_number: int = 1,
    ) -> CoordinatedStepResult:
        if run.state not in {
            ExecutionRunState.READY,
            ExecutionRunState.RUNNING,
        }:
            raise ExecutionStateError(
                "Execution run must be ready or running."
            )

        graph_result = self.graph_builder.build(run)
        states = {
            step.step_id: step.state
            for step in run.steps
        }
        schedule = build_execution_schedule(
            graph=graph_result.graph,
            step_states=states,
        )

        if schedule.next_step_id is None:
            raise ExecutionContractError(
                "Execution run has no eligible step."
            )

        selected = self._step_by_id(
            run.steps,
            schedule.next_step_id,
        )
        outcome = self.executor.execute(
            run_id=run.run_id,
            step=selected,
            attempt_number=attempt_number,
            invocations=invocations_by_step.get(
                selected.step_id,
                (),
            ),
            authority=authority,
        )
        updated_steps = tuple(
            self._updated_step(
                step,
                selected_step_id=selected.step_id,
                outcome=outcome,
            )
            for step in run.steps
        )
        all_succeeded = all(
            step.state is ExecutionStepState.SUCCEEDED
            for step in updated_steps
        )
        updated_run = run.model_copy(
            update={
                "state": (
                    ExecutionRunState.SUCCEEDED
                    if all_succeeded
                    else (
                        ExecutionRunState.RUNNING
                        if outcome.succeeded
                        else ExecutionRunState.FAILED
                    )
                ),
                "steps": updated_steps,
                "current_step_id": (
                    None
                    if all_succeeded
                    else selected.step_id
                ),
                "failure_reason": (
                    outcome.attempt.failure_reason
                    if not outcome.succeeded
                    else None
                ),
            }
        )

        return CoordinatedStepResult(
            run=updated_run,
            outcome=outcome,
        )

    @staticmethod
    def _step_by_id(
        steps: tuple[ExecutionStep, ...],
        step_id: str,
    ) -> ExecutionStep:
        for step in steps:
            if step.step_id == step_id:
                return step

        raise ExecutionContractError(
            f"Unknown execution step: {step_id}"
        )

    @staticmethod
    def _updated_step(
        step: ExecutionStep,
        *,
        selected_step_id: str,
        outcome: StepExecutionOutcome,
    ) -> ExecutionStep:
        if step.step_id != selected_step_id:
            return step

        return step.model_copy(
            update={
                "state": (
                    ExecutionStepState.SUCCEEDED
                    if outcome.succeeded
                    else ExecutionStepState.FAILED
                )
            }
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_authority.py" @'
import pytest

from forge.autonomous_execution_v2.authority import (
    ExecutionAuthority,
    assert_step_authorized,
)
from forge.autonomous_execution_v2.errors import (
    ExecutionAuthorityError,
)
from forge.autonomous_execution_v2.models import ExecutionStep
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)


def test_authority_rejects_missing_tool() -> None:
    step = ExecutionStep(
        step_id="step-1",
        planning_step_id="planning-step-1",
        sequence=1,
        name="Edit",
        description="Apply controlled repository edit.",
        required_tools=("filesystem",),
    )

    with pytest.raises(ExecutionAuthorityError):
        assert_step_authorized(
            step=step,
            authority=ExecutionAuthority(
                subject="agent",
                repository_root="repository",
            ),
            policy=AutonomousExecutionV2Policy(),
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_attempts.py" @'
import pytest

from forge.autonomous_execution_v2.attempts import (
    complete_attempt,
    create_attempt,
    start_attempt,
)
from forge.autonomous_execution_v2.errors import (
    ExecutionContractError,
)
from forge.autonomous_execution_v2.states import (
    ExecutionAttemptState,
)


def test_attempt_lifecycle_succeeds() -> None:
    attempt = create_attempt(
        run_id="run-1",
        step_id="step-1",
        attempt_number=1,
    )
    running = start_attempt(attempt)
    completed = complete_attempt(
        running,
        succeeded=True,
        tool_invocation_ids=("invocation-1",),
    )

    assert completed.state is ExecutionAttemptState.SUCCEEDED


def test_failed_attempt_requires_reason() -> None:
    attempt = start_attempt(
        create_attempt(
            run_id="run-1",
            step_id="step-1",
            attempt_number=1,
        )
    )

    with pytest.raises(ExecutionContractError):
        complete_attempt(
            attempt,
            succeeded=False,
            tool_invocation_ids=(),
        )
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_evidence.py" @'
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
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_step_execution.py" @'
from dataclasses import dataclass, field

from forge.autonomous_execution_v2.authority import (
    ExecutionAuthority,
)
from forge.autonomous_execution_v2.models import ExecutionStep
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)
from forge.autonomous_execution_v2.step_execution import (
    ControlledStepExecutor,
    StepToolInvocation,
)
from forge.autonomous_execution_v2.tool_adapter import (
    ControlledToolRequest,
    ControlledToolResult,
)


@dataclass
class FakeGateway:
    requests: list[ControlledToolRequest] = field(
        default_factory=list
    )

    def execute(
        self,
        request: ControlledToolRequest,
    ) -> ControlledToolResult:
        self.requests.append(request)
        return ControlledToolResult(
            invocation_id=request.invocation_id,
            succeeded=True,
            output_references=("result-1",),
            summary="Completed.",
        )


def test_step_executes_through_gateway() -> None:
    gateway = FakeGateway()
    outcome = ControlledStepExecutor(
        gateway=gateway,
        policy=AutonomousExecutionV2Policy(),
    ).execute(
        run_id="run-1",
        step=ExecutionStep(
            step_id="step-1",
            planning_step_id="planning-step-1",
            sequence=1,
            name="Validate",
            description="Run controlled validation.",
            required_tools=("test",),
        ),
        attempt_number=1,
        invocations=(
            StepToolInvocation(
                invocation_id="invocation-1",
                tool_name="test",
                arguments={"target": "tests"},
            ),
        ),
        authority=ExecutionAuthority(
            subject="agent",
            repository_root="repository",
            permitted_tools=("test",),
        ),
    )

    assert outcome.succeeded
    assert len(outcome.evidence) == 1
    assert len(gateway.requests) == 1
'@

Write-Utf8NoBom "tests\test_autonomous_execution_v2_coordinator.py" @'
from dataclasses import dataclass

from forge.autonomous_execution_v2.authority import (
    ExecutionAuthority,
)
from forge.autonomous_execution_v2.coordinator import (
    AutonomousExecutionCoordinator,
)
from forge.autonomous_execution_v2.graph_builder import (
    ExecutionGraphBuilder,
)
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
)
from forge.autonomous_execution_v2.states import (
    ExecutionRunState,
    ExecutionStepState,
)
from forge.autonomous_execution_v2.step_execution import (
    ControlledStepExecutor,
    StepToolInvocation,
)
from forge.autonomous_execution_v2.tool_adapter import (
    ControlledToolRequest,
    ControlledToolResult,
)


@dataclass
class FakeGateway:
    def execute(
        self,
        request: ControlledToolRequest,
    ) -> ControlledToolResult:
        return ControlledToolResult(
            invocation_id=request.invocation_id,
            succeeded=True,
            output_references=("result-1",),
            summary="Completed.",
        )


def test_coordinator_executes_next_step() -> None:
    policy = AutonomousExecutionV2Policy()
    run = ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        state=ExecutionRunState.READY,
        steps=(
            ExecutionStep(
                step_id="step-1",
                planning_step_id="planning-step-1",
                sequence=1,
                name="Validate",
                description="Run controlled validation.",
                required_tools=("test",),
            ),
        ),
    )
    result = AutonomousExecutionCoordinator(
        graph_builder=ExecutionGraphBuilder(
            policy=policy
        ),
        executor=ControlledStepExecutor(
            gateway=FakeGateway(),
            policy=policy,
        ),
    ).execute_next(
        run=run,
        invocations_by_step={
            "step-1": (
                StepToolInvocation(
                    invocation_id="invocation-1",
                    tool_name="test",
                    arguments={},
                ),
            )
        },
        authority=ExecutionAuthority(
            subject="agent",
            repository_root="repository",
            permitted_tools=("test",),
        ),
    )

    assert result.run.state is ExecutionRunState.SUCCEEDED
    assert (
        result.run.steps[0].state
        is ExecutionStepState.SUCCEEDED
    )
'@

Write-Host ""
Write-Host "M5.7 Package 2 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_execution_v2_authority.py `
    .\tests\test_autonomous_execution_v2_attempts.py `
    .\tests\test_autonomous_execution_v2_evidence.py `
    .\tests\test_autonomous_execution_v2_step_execution.py `
    .\tests\test_autonomous_execution_v2_coordinator.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.7 Package 2 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full repository tests"

Write-Host ""
Write-Host "M5.7 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short