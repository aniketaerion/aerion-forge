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

$ExpectedBranch = "feature/m5.6-autonomous-planning-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.6 Package 3 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_planning\validation.py" @'
"""Validation rules for generated autonomous plans."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.cycle_detection import find_cycle
from forge.autonomous_planning.graph_builder import PlanningGraphBuilder
from forge.autonomous_planning.identifiers import (
    deterministic_identifier,
)
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningValidationFinding,
    PlanningValidationResult,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.states import (
    ApprovalRequirement,
    PlanningRisk,
    StepKind,
)


@dataclass(frozen=True, slots=True)
class AutonomousPlanValidator:
    """Validate plan safety, completeness, and graph integrity."""

    policy: AutonomousPlanningPolicy

    def validate(
        self,
        plan: PlanningPlan,
    ) -> PlanningValidationResult:
        findings: list[PlanningValidationFinding] = []

        if len(plan.steps) > self.policy.limits.maximum_steps:
            findings.append(
                self._finding(
                    code="MAXIMUM_STEPS_EXCEEDED",
                    message="Plan exceeds the configured step limit.",
                    severity=PlanningRisk.HIGH,
                    blocking=True,
                )
            )

        if (
            len(plan.dependencies)
            > self.policy.limits.maximum_dependencies
        ):
            findings.append(
                self._finding(
                    code="MAXIMUM_DEPENDENCIES_EXCEEDED",
                    message=(
                        "Plan exceeds the configured dependency limit."
                    ),
                    severity=PlanningRisk.HIGH,
                    blocking=True,
                )
            )

        names = [step.name for step in plan.steps]

        if (
            self.policy.quality.require_unique_step_names
            and len(names) != len(set(names))
        ):
            findings.append(
                self._finding(
                    code="DUPLICATE_STEP_NAMES",
                    message="Planning step names must be unique.",
                    severity=PlanningRisk.MEDIUM,
                    blocking=True,
                )
            )

        if (
            self.policy.safety.require_validation_step
            and not any(
                step.kind is StepKind.VALIDATION
                for step in plan.steps
            )
        ):
            findings.append(
                self._finding(
                    code="VALIDATION_STEP_MISSING",
                    message=(
                        "Plan requires at least one validation step."
                    ),
                    severity=PlanningRisk.HIGH,
                    blocking=True,
                )
            )

        for step in plan.steps:
            if (
                len(step.description)
                < self.policy.quality.minimum_step_description_length
            ):
                findings.append(
                    self._finding(
                        code="STEP_DESCRIPTION_TOO_SHORT",
                        message=(
                            "Planning step description is too short."
                        ),
                        severity=PlanningRisk.MEDIUM,
                        blocking=True,
                        step_id=step.step_id,
                    )
                )

            if (
                step.destructive
                and not self.policy.safety.allow_destructive_steps
            ):
                findings.append(
                    self._finding(
                        code="DESTRUCTIVE_STEP_FORBIDDEN",
                        message=(
                            "Destructive planning steps are forbidden "
                            "by policy."
                        ),
                        severity=PlanningRisk.CRITICAL,
                        blocking=True,
                        step_id=step.step_id,
                    )
                )

            if (
                step.risk
                in {PlanningRisk.HIGH, PlanningRisk.CRITICAL}
                and self.policy.safety.require_approval_for_high_risk
                and step.approval_requirement
                is ApprovalRequirement.NONE
            ):
                findings.append(
                    self._finding(
                        code="HIGH_RISK_APPROVAL_MISSING",
                        message=(
                            "High-risk planning step requires approval."
                        ),
                        severity=PlanningRisk.HIGH,
                        blocking=True,
                        step_id=step.step_id,
                    )
                )

        try:
            graph_result = PlanningGraphBuilder(
                policy=self.policy
            ).build(plan)
            cycle = find_cycle(graph_result.graph)
        except Exception as exc:
            findings.append(
                self._finding(
                    code="GRAPH_BUILD_FAILED",
                    message=str(exc),
                    severity=PlanningRisk.HIGH,
                    blocking=True,
                )
            )
        else:
            if cycle is not None:
                findings.append(
                    self._finding(
                        code="DEPENDENCY_CYCLE",
                        message=(
                            "Planning graph contains cycle: "
                            + " -> ".join(cycle)
                        ),
                        severity=PlanningRisk.HIGH,
                        blocking=True,
                    )
                )

        ordered = tuple(
            sorted(
                findings,
                key=lambda item: (
                    not item.blocking,
                    item.severity.value,
                    item.code,
                    item.step_id or "",
                ),
            )
        )
        valid = not any(
            finding.blocking
            for finding in ordered
        )

        return PlanningValidationResult(
            plan_id=plan.plan_id,
            valid=valid,
            findings=ordered,
        )

    @staticmethod
    def _finding(
        *,
        code: str,
        message: str,
        severity: PlanningRisk,
        blocking: bool,
        step_id: str | None = None,
    ) -> PlanningValidationFinding:
        payload = {
            "code": code,
            "message": message,
            "severity": severity.value,
            "blocking": blocking,
            "step_id": step_id,
        }
        return PlanningValidationFinding(
            finding_id=deterministic_identifier(
                "planning-finding",
                payload,
            ),
            severity=severity,
            code=code,
            message=message,
            step_id=step_id,
            blocking=blocking,
        )
'@

Write-Utf8NoBom "forge\autonomous_planning\approval.py" @'
"""Plan approval and rejection controls."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from forge.autonomous_planning.errors import (
    PlanningStateError,
)
from forge.autonomous_planning.models import PlanningPlan
from forge.autonomous_planning.states import PlanningState


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class PlanningApprovalDecision:
    """Recorded human or policy approval decision."""

    plan_id: str
    approved: bool
    decided_by: str
    rationale: str
    decided_at: datetime


def approve_plan(
    *,
    plan: PlanningPlan,
    decided_by: str,
    rationale: str,
) -> tuple[PlanningPlan, PlanningApprovalDecision]:
    """Approve a plan that is awaiting approval."""
    if plan.state is not PlanningState.AWAITING_APPROVAL:
        raise PlanningStateError(
            "Only plans awaiting approval can be approved."
        )

    if not decided_by.strip():
        raise ValueError("Approver cannot be empty.")

    if not rationale.strip():
        raise ValueError("Approval rationale cannot be empty.")

    now = utc_now()
    approved = plan.model_copy(
        update={
            "state": PlanningState.READY,
            "updated_at": now,
        }
    )
    decision = PlanningApprovalDecision(
        plan_id=plan.plan_id,
        approved=True,
        decided_by=decided_by,
        rationale=rationale,
        decided_at=now,
    )
    return approved, decision


def reject_plan(
    *,
    plan: PlanningPlan,
    decided_by: str,
    rationale: str,
) -> tuple[PlanningPlan, PlanningApprovalDecision]:
    """Reject a plan that is awaiting approval."""
    if plan.state is not PlanningState.AWAITING_APPROVAL:
        raise PlanningStateError(
            "Only plans awaiting approval can be rejected."
        )

    if not decided_by.strip():
        raise ValueError("Rejector cannot be empty.")

    if not rationale.strip():
        raise ValueError("Rejection rationale cannot be empty.")

    now = utc_now()
    rejected = plan.model_copy(
        update={
            "state": PlanningState.REJECTED,
            "updated_at": now,
        }
    )
    decision = PlanningApprovalDecision(
        plan_id=plan.plan_id,
        approved=False,
        decided_by=decided_by,
        rationale=rationale,
        decided_at=now,
    )
    return rejected, decision
'@

Write-Utf8NoBom "forge\autonomous_planning\revision.py" @'
"""Immutable planning-plan revision support."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.errors import PlanningContractError
from forge.autonomous_planning.identifiers import (
    planning_plan_identifier,
)
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.states import PlanningState


@dataclass(frozen=True, slots=True)
class PlanRevision:
    """Previous and revised immutable planning plans."""

    previous: PlanningPlan
    revised: PlanningPlan
    rationale: str


def revise_plan(
    *,
    plan: PlanningPlan,
    steps: tuple[PlanningStep, ...] | None = None,
    dependencies: tuple[PlanningDependency, ...] | None = None,
    warnings: tuple[str, ...] | None = None,
    rationale: str,
) -> PlanRevision:
    """Create the next immutable version of a plan."""
    if not rationale.strip():
        raise PlanningContractError(
            "Plan revision rationale cannot be empty."
        )

    revised_steps = steps or plan.steps
    revised_dependencies = (
        dependencies
        if dependencies is not None
        else plan.dependencies
    )
    revised_warnings = (
        warnings
        if warnings is not None
        else plan.warnings
    )
    next_version = plan.version + 1

    payload = {
        "request_id": plan.request_id,
        "version": next_version,
        "steps": tuple(
            step.step_id
            for step in revised_steps
        ),
        "dependencies": tuple(
            dependency.dependency_id
            for dependency in revised_dependencies
        ),
        "rationale": rationale,
    }

    revised = plan.model_copy(
        update={
            "plan_id": planning_plan_identifier(payload),
            "version": next_version,
            "state": PlanningState.VALIDATING,
            "steps": revised_steps,
            "dependencies": revised_dependencies,
            "warnings": revised_warnings,
        }
    )

    return PlanRevision(
        previous=plan,
        revised=revised,
        rationale=rationale,
    )
'@

Write-Utf8NoBom "forge\autonomous_planning\repository.py" @'
"""In-memory planning repository with optimistic version checks."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_planning.errors import PlanningContractError
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningRequest,
    PlanningSession,
)


@dataclass(slots=True)
class InMemoryPlanningRepository:
    """Deterministic repository for planning aggregates."""

    _requests: dict[str, PlanningRequest] = field(
        default_factory=dict
    )
    _plans: dict[str, PlanningPlan] = field(
        default_factory=dict
    )
    _sessions: dict[str, PlanningSession] = field(
        default_factory=dict
    )

    def put_request(
        self,
        request: PlanningRequest,
    ) -> None:
        existing = self._requests.get(request.request_id)

        if existing is not None and existing != request:
            raise PlanningContractError(
                f"Conflicting planning request: "
                f"{request.request_id}"
            )

        self._requests[request.request_id] = request

    def get_request(
        self,
        request_id: str,
    ) -> PlanningRequest | None:
        return self._requests.get(request_id)

    def put_plan(
        self,
        plan: PlanningPlan,
        *,
        expected_version: int | None = None,
    ) -> None:
        existing = self._plans.get(plan.plan_id)

        if (
            expected_version is not None
            and existing is not None
            and existing.version != expected_version
        ):
            raise PlanningContractError(
                "Planning plan version conflict."
            )

        self._plans[plan.plan_id] = plan

    def get_plan(
        self,
        plan_id: str,
    ) -> PlanningPlan | None:
        return self._plans.get(plan_id)

    def put_session(
        self,
        session: PlanningSession,
    ) -> None:
        existing = self._sessions.get(session.session_id)

        if existing is not None and existing != session:
            raise PlanningContractError(
                f"Conflicting planning session: "
                f"{session.session_id}"
            )

        self._sessions[session.session_id] = session

    def get_session(
        self,
        session_id: str,
    ) -> PlanningSession | None:
        return self._sessions.get(session_id)

    def all_plans(self) -> tuple[PlanningPlan, ...]:
        return tuple(
            self._plans[key]
            for key in sorted(self._plans)
        )
'@

Write-Utf8NoBom "forge\autonomous_planning\service.py" @'
"""Application service for autonomous planning."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_planning.approval import (
    PlanningApprovalDecision,
    approve_plan,
    reject_plan,
)
from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningRequest,
    PlanningValidationResult,
)
from forge.autonomous_planning.plan_generation import (
    AutonomousPlanGenerator,
    GeneratedPlan,
)
from forge.autonomous_planning.repository import (
    InMemoryPlanningRepository,
)
from forge.autonomous_planning.validation import (
    AutonomousPlanValidator,
)


@dataclass(slots=True)
class AutonomousPlanningService:
    """Generate, validate, approve, and persist plans."""

    generator: AutonomousPlanGenerator
    validator: AutonomousPlanValidator
    repository: InMemoryPlanningRepository

    def create_plan(
        self,
        *,
        request: PlanningRequest,
        context: PlanningContext,
    ) -> tuple[GeneratedPlan, PlanningValidationResult]:
        self.repository.put_request(request)
        generated = self.generator.generate(
            request=request,
            context=context,
        )
        validation = self.validator.validate(
            generated.plan
        )

        if not validation.valid:
            failed = generated.plan.model_copy(
                update={"state": "failed"}
            )
            self.repository.put_plan(failed)
            generated = GeneratedPlan(
                analysis=generated.analysis,
                plan=failed,
                ordered_step_ids=generated.ordered_step_ids,
            )
        else:
            self.repository.put_plan(generated.plan)

        return generated, validation

    def approve(
        self,
        *,
        plan: PlanningPlan,
        decided_by: str,
        rationale: str,
    ) -> tuple[PlanningPlan, PlanningApprovalDecision]:
        approved, decision = approve_plan(
            plan=plan,
            decided_by=decided_by,
            rationale=rationale,
        )
        self.repository.put_plan(approved)
        return approved, decision

    def reject(
        self,
        *,
        plan: PlanningPlan,
        decided_by: str,
        rationale: str,
    ) -> tuple[PlanningPlan, PlanningApprovalDecision]:
        rejected, decision = reject_plan(
            plan=plan,
            decided_by=decided_by,
            rationale=rationale,
        )
        self.repository.put_plan(rejected)
        return rejected, decision
'@

Write-Utf8NoBom "tests\test_autonomous_planning_validation.py" @'
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.states import (
    PlanningRisk,
    StepKind,
)
from forge.autonomous_planning.validation import (
    AutonomousPlanValidator,
)


def test_validator_rejects_plan_without_validation_step() -> None:
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Analyse",
                description=(
                    "Analyse repository impact before changes."
                ),
                kind=StepKind.ANALYSIS,
                risk=PlanningRisk.LOW,
            ),
        ),
    )

    result = AutonomousPlanValidator(
        policy=AutonomousPlanningPolicy()
    ).validate(plan)

    assert not result.valid
    assert any(
        finding.code == "VALIDATION_STEP_MISSING"
        for finding in result.findings
    )
'@

Write-Utf8NoBom "tests\test_autonomous_planning_approval.py" @'
import pytest

from forge.autonomous_planning.approval import (
    approve_plan,
    reject_plan,
)
from forge.autonomous_planning.errors import (
    PlanningStateError,
)
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.states import (
    PlanningState,
    StepKind,
)


def plan(state: PlanningState) -> PlanningPlan:
    return PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        state=state,
        summary="Plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
                kind=StepKind.VALIDATION,
            ),
        ),
    )


def test_approve_moves_plan_to_ready() -> None:
    approved, decision = approve_plan(
        plan=plan(PlanningState.AWAITING_APPROVAL),
        decided_by="Aerion",
        rationale="Risk accepted.",
    )

    assert approved.state is PlanningState.READY
    assert decision.approved


def test_reject_moves_plan_to_rejected() -> None:
    rejected, decision = reject_plan(
        plan=plan(PlanningState.AWAITING_APPROVAL),
        decided_by="Aerion",
        rationale="Risk too high.",
    )

    assert rejected.state is PlanningState.REJECTED
    assert not decision.approved


def test_ready_plan_cannot_be_approved_again() -> None:
    with pytest.raises(PlanningStateError):
        approve_plan(
            plan=plan(PlanningState.READY),
            decided_by="Aerion",
            rationale="Already ready.",
        )
'@

Write-Utf8NoBom "tests\test_autonomous_planning_revision.py" @'
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.revision import revise_plan
from forge.autonomous_planning.states import (
    PlanningState,
    StepKind,
)


def test_revision_increments_version() -> None:
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
                kind=StepKind.VALIDATION,
            ),
        ),
    )

    revision = revise_plan(
        plan=plan,
        rationale="Add validation evidence.",
    )

    assert revision.revised.version == 2
    assert revision.revised.plan_id != plan.plan_id
    assert (
        revision.revised.state
        is PlanningState.VALIDATING
    )
'@

Write-Utf8NoBom "tests\test_autonomous_planning_repository.py" @'
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
)
from forge.autonomous_planning.repository import (
    InMemoryPlanningRepository,
)
from forge.autonomous_planning.states import StepKind


def test_repository_persists_plan() -> None:
    repository = InMemoryPlanningRepository()
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
                kind=StepKind.VALIDATION,
            ),
        ),
    )

    repository.put_plan(plan)

    assert repository.get_plan("plan-1") == plan
    assert repository.all_plans() == (plan,)
'@

Write-Utf8NoBom "tests\test_autonomous_planning_service.py" @'
from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.models import PlanningRequest
from forge.autonomous_planning.plan_generation import (
    AutonomousPlanGenerator,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.repository import (
    InMemoryPlanningRepository,
)
from forge.autonomous_planning.service import (
    AutonomousPlanningService,
)
from forge.autonomous_planning.states import (
    PlanningIntent,
    PlanningState,
)
from forge.autonomous_planning.validation import (
    AutonomousPlanValidator,
)


def test_service_creates_valid_plan() -> None:
    policy = AutonomousPlanningPolicy()
    service = AutonomousPlanningService(
        generator=AutonomousPlanGenerator(
            policy=policy
        ),
        validator=AutonomousPlanValidator(
            policy=policy
        ),
        repository=InMemoryPlanningRepository(),
    )

    generated, validation = service.create_plan(
        request=PlanningRequest(
            request_id="request-1",
            objective="Implement feature",
            repository_root="repository",
            intent=PlanningIntent.IMPLEMENT_FEATURE,
            acceptance_criteria=("Tests pass",),
            created_by="Aerion",
        ),
        context=PlanningContext(
            repository_root="repository",
            repository_fingerprint="fingerprint-1",
            validation_commands=("python -m pytest",),
        ),
    )

    assert validation.valid
    assert generated.plan.state is PlanningState.READY
    assert (
        service.repository.get_plan(
            generated.plan.plan_id
        )
        == generated.plan
    )
'@

Write-Host ""
Write-Host "M5.6 Package 3 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_planning_validation.py `
    .\tests\test_autonomous_planning_approval.py `
    .\tests\test_autonomous_planning_revision.py `
    .\tests\test_autonomous_planning_repository.py `
    .\tests\test_autonomous_planning_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.6 Package 3 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.6 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short