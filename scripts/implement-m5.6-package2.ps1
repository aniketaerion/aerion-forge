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
    throw "M5.6 Package 2 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_planning\context.py" @'
"""Repository-grounded planning context."""

from __future__ import annotations

from itertools import pairwise

from pydantic import BaseModel, ConfigDict


class PlanningContext(BaseModel):
    """Evidence and constraints used to generate a plan."""

    model_config = ConfigDict(frozen=True)

    repository_root: str
    repository_fingerprint: str
    known_modules: tuple[str, ...] = ()
    known_capabilities: tuple[str, ...] = ()
    relevant_files: tuple[str, ...] = ()
    validation_commands: tuple[str, ...] = ()
    architecture_constraints: tuple[str, ...] = ()
    operational_constraints: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
'@

Write-Utf8NoBom "forge\autonomous_planning\analysis.py" @'
"""Planning request analysis."""

from __future__ import annotations

from itertools import pairwise

from dataclasses import dataclass

from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.models import PlanningRequest
from forge.autonomous_planning.states import PlanningRisk


@dataclass(frozen=True, slots=True)
class PlanningAnalysis:
    """Normalized analysis of a planning request."""

    objective: str
    target_paths: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    constraints: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    validation_commands: tuple[str, ...]
    architecture_constraints: tuple[str, ...]
    evidence_references: tuple[str, ...]
    estimated_risk: PlanningRisk
    warnings: tuple[str, ...]


def analyse_planning_request(
    *,
    request: PlanningRequest,
    context: PlanningContext,
) -> PlanningAnalysis:
    """Produce deterministic repository-grounded planning analysis."""
    target_paths = tuple(
        sorted(
            set(request.target_paths)
            | set(context.relevant_files)
        )
    )
    capabilities = tuple(
        sorted(
            set(request.requested_capabilities)
            | set(context.known_capabilities)
        )
    )
    constraints = tuple(
        sorted(
            set(request.constraints)
            | set(context.operational_constraints)
        )
    )
    architecture = tuple(
        sorted(set(context.architecture_constraints))
    )
    evidence = tuple(
        sorted(set(context.evidence_references))
    )

    warnings: list[str] = []
    risk = PlanningRisk.LOW

    if len(target_paths) > 10:
        risk = PlanningRisk.MEDIUM
        warnings.append(
            "Plan affects more than ten repository paths."
        )

    if any(
        token in request.objective.casefold()
        for token in (
            "delete",
            "drop",
            "migrate",
            "release",
            "production",
        )
    ):
        risk = PlanningRisk.HIGH
        warnings.append(
            "Objective contains a high-impact operation."
        )

    if not request.acceptance_criteria:
        warnings.append(
            "Planning request has no explicit acceptance criteria."
        )

    return PlanningAnalysis(
        objective=request.objective.strip(),
        target_paths=target_paths,
        required_capabilities=capabilities,
        constraints=constraints,
        acceptance_criteria=tuple(
            sorted(set(request.acceptance_criteria))
        ),
        validation_commands=tuple(
            sorted(set(context.validation_commands))
        ),
        architecture_constraints=architecture,
        evidence_references=evidence,
        estimated_risk=risk,
        warnings=tuple(warnings),
    )
'@

Write-Utf8NoBom "forge\autonomous_planning\step_synthesis.py" @'
"""Deterministic planning-step synthesis."""

from __future__ import annotations

from itertools import pairwise

from forge.autonomous_planning.analysis import PlanningAnalysis
from forge.autonomous_planning.identifiers import (
    planning_step_identifier,
)
from forge.autonomous_planning.models import PlanningStep
from forge.autonomous_planning.states import (
    ApprovalRequirement,
    PlanningIntent,
    PlanningRisk,
    StepKind,
)


def _step(
    *,
    sequence: int,
    name: str,
    description: str,
    kind: StepKind,
    analysis: PlanningAnalysis,
    risk: PlanningRisk,
    approval: ApprovalRequirement = ApprovalRequirement.NONE,
    target_paths: tuple[str, ...] = (),
    expected_outputs: tuple[str, ...] = (),
    acceptance_criteria: tuple[str, ...] = (),
) -> PlanningStep:
    payload = {
        "sequence": sequence,
        "name": name,
        "description": description,
        "kind": kind.value,
        "target_paths": target_paths,
        "risk": risk.value,
    }

    return PlanningStep(
        step_id=planning_step_identifier(payload),
        sequence=sequence,
        name=name,
        description=description,
        kind=kind,
        target_paths=target_paths,
        required_capabilities=analysis.required_capabilities,
        expected_outputs=expected_outputs,
        acceptance_criteria=acceptance_criteria,
        risk=risk,
        approval_requirement=approval,
        destructive=False,
    )


def synthesize_steps(
    *,
    intent: PlanningIntent,
    analysis: PlanningAnalysis,
) -> tuple[PlanningStep, ...]:
    """Create a bounded, deterministic plan skeleton."""
    steps: list[PlanningStep] = []

    steps.append(
        _step(
            sequence=1,
            name="Analyse repository impact",
            description=(
                "Inspect affected modules, constraints, and evidence "
                "before proposing repository changes."
            ),
            kind=StepKind.ANALYSIS,
            analysis=analysis,
            risk=PlanningRisk.LOW,
            target_paths=analysis.target_paths,
            expected_outputs=("impact-analysis",),
        )
    )

    if intent is PlanningIntent.INVESTIGATE:
        steps.append(
            _step(
                sequence=2,
                name="Produce investigation findings",
                description=(
                    "Produce evidence-backed findings without changing "
                    "repository state."
                ),
                kind=StepKind.ANALYSIS,
                analysis=analysis,
                risk=analysis.estimated_risk,
                expected_outputs=("investigation-report",),
                acceptance_criteria=analysis.acceptance_criteria,
            )
        )
    elif intent is PlanningIntent.DOCUMENT:
        steps.append(
            _step(
                sequence=2,
                name="Update documentation",
                description=(
                    "Update repository documentation while preserving "
                    "architecture terminology and traceability."
                ),
                kind=StepKind.DOCUMENTATION,
                analysis=analysis,
                risk=PlanningRisk.LOW,
                target_paths=analysis.target_paths,
                expected_outputs=("documentation-update",),
                acceptance_criteria=analysis.acceptance_criteria,
            )
        )
    else:
        approval = (
            ApprovalRequirement.PLAN
            if analysis.estimated_risk
            in {PlanningRisk.HIGH, PlanningRisk.CRITICAL}
            else ApprovalRequirement.NONE
        )
        steps.append(
            _step(
                sequence=2,
                name="Implement planned change",
                description=(
                    "Apply the smallest repository-grounded change "
                    "that satisfies the approved objective."
                ),
                kind=StepKind.CODE_CHANGE,
                analysis=analysis,
                risk=analysis.estimated_risk,
                approval=approval,
                target_paths=analysis.target_paths,
                expected_outputs=("repository-change",),
                acceptance_criteria=analysis.acceptance_criteria,
            )
        )
        steps.append(
            _step(
                sequence=3,
                name="Run focused tests",
                description=(
                    "Run tests focused on the changed behaviour and "
                    "affected modules."
                ),
                kind=StepKind.TEST,
                analysis=analysis,
                risk=PlanningRisk.LOW,
                expected_outputs=("focused-test-results",),
            )
        )

    steps.append(
        _step(
            sequence=len(steps) + 1,
            name="Validate repository",
            description=(
                "Run configured quality, typing, and repository "
                "regression checks before completion."
            ),
            kind=StepKind.VALIDATION,
            analysis=analysis,
            risk=PlanningRisk.LOW,
            expected_outputs=analysis.validation_commands
            or ("validation-results",),
            acceptance_criteria=analysis.acceptance_criteria,
        )
    )

    return tuple(steps)
'@

Write-Utf8NoBom "forge\autonomous_planning\dependency_synthesis.py" @'
"""Deterministic dependency synthesis for planning steps."""

from __future__ import annotations

from itertools import pairwise

from forge.autonomous_planning.identifiers import (
    planning_dependency_identifier,
)
from forge.autonomous_planning.models import (
    PlanningDependency,
    PlanningStep,
)
from forge.autonomous_planning.states import DependencyKind


def synthesize_linear_dependencies(
    steps: tuple[PlanningStep, ...],
) -> tuple[PlanningDependency, ...]:
    """Create strict prerequisite dependencies by sequence."""
    ordered = tuple(
        sorted(
            steps,
            key=lambda item: (
                item.sequence,
                item.step_id,
            ),
        )
    )
    dependencies: list[PlanningDependency] = []

    for previous, current in pairwise(ordered):
        payload = {
            "source": current.step_id,
            "target": previous.step_id,
            "kind": DependencyKind.REQUIRES.value,
        }
        dependencies.append(
            PlanningDependency(
                dependency_id=planning_dependency_identifier(
                    payload
                ),
                source_step_id=current.step_id,
                target_step_id=previous.step_id,
                kind=DependencyKind.REQUIRES,
                rationale=(
                    f"{current.name} requires completion of "
                    f"{previous.name}."
                ),
            )
        )

    return tuple(dependencies)
'@

Write-Utf8NoBom "forge\autonomous_planning\plan_generation.py" @'
"""Autonomous plan generation service."""

from __future__ import annotations

from itertools import pairwise

from dataclasses import dataclass

from forge.autonomous_planning.analysis import (
    PlanningAnalysis,
    analyse_planning_request,
)
from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.dependency_synthesis import (
    synthesize_linear_dependencies,
)
from forge.autonomous_planning.graph_builder import (
    PlanningGraphBuilder,
)
from forge.autonomous_planning.identifiers import (
    planning_plan_identifier,
)
from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningRequest,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.states import (
    PlanningRisk,
    PlanningState,
)
from forge.autonomous_planning.step_synthesis import (
    synthesize_steps,
)


@dataclass(frozen=True, slots=True)
class GeneratedPlan:
    """Generated plan and the analysis that produced it."""

    analysis: PlanningAnalysis
    plan: PlanningPlan
    ordered_step_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AutonomousPlanGenerator:
    """Generate deterministic, repository-grounded plans."""

    policy: AutonomousPlanningPolicy

    def generate(
        self,
        *,
        request: PlanningRequest,
        context: PlanningContext,
    ) -> GeneratedPlan:
        analysis = analyse_planning_request(
            request=request,
            context=context,
        )
        steps = synthesize_steps(
            intent=request.intent,
            analysis=analysis,
        )
        dependencies = synthesize_linear_dependencies(
            steps
        )
        requires_approval = any(
            step.approval_requirement.value != "none"
            for step in steps
        )
        risk = max(
            (step.risk for step in steps),
            key=lambda item: (
                PlanningRisk.LOW,
                PlanningRisk.MEDIUM,
                PlanningRisk.HIGH,
                PlanningRisk.CRITICAL,
            ).index(item),
        )
        payload = {
            "request_id": request.request_id,
            "objective": analysis.objective,
            "steps": tuple(
                step.step_id
                for step in steps
            ),
            "dependencies": tuple(
                dependency.dependency_id
                for dependency in dependencies
            ),
        }
        state = (
            PlanningState.AWAITING_APPROVAL
            if requires_approval
            else PlanningState.READY
        )
        plan = PlanningPlan(
            plan_id=planning_plan_identifier(payload),
            request_id=request.request_id,
            state=state,
            summary=(
                "Repository-grounded autonomous plan for: "
                f"{analysis.objective}"
            ),
            steps=steps,
            dependencies=dependencies,
            risk=risk,
            requires_approval=requires_approval,
            warnings=analysis.warnings,
        )
        graph_result = PlanningGraphBuilder(
            policy=self.policy
        ).build(plan)

        return GeneratedPlan(
            analysis=analysis,
            plan=plan,
            ordered_step_ids=graph_result.ordered_step_ids,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_planning_analysis.py" @'
from forge.autonomous_planning.analysis import (
    analyse_planning_request,
)
from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.models import PlanningRequest
from forge.autonomous_planning.states import (
    PlanningIntent,
    PlanningRisk,
)


def test_analysis_merges_repository_context() -> None:
    result = analyse_planning_request(
        request=PlanningRequest(
            request_id="request-1",
            objective="Implement feature",
            repository_root="repository",
            intent=PlanningIntent.IMPLEMENT_FEATURE,
            target_paths=("forge/a.py",),
            requested_capabilities=("editing",),
            created_by="Aerion",
        ),
        context=PlanningContext(
            repository_root="repository",
            repository_fingerprint="fingerprint-1",
            relevant_files=("forge/b.py",),
            known_capabilities=("testing",),
        ),
    )

    assert result.target_paths == (
        "forge/a.py",
        "forge/b.py",
    )
    assert result.required_capabilities == (
        "editing",
        "testing",
    )
    assert result.estimated_risk is PlanningRisk.LOW
'@

Write-Utf8NoBom "tests\test_autonomous_planning_step_synthesis.py" @'
from forge.autonomous_planning.analysis import (
    PlanningAnalysis,
)
from forge.autonomous_planning.states import (
    PlanningIntent,
    PlanningRisk,
    StepKind,
)
from forge.autonomous_planning.step_synthesis import (
    synthesize_steps,
)


def analysis() -> PlanningAnalysis:
    return PlanningAnalysis(
        objective="Implement feature",
        target_paths=("forge/a.py",),
        required_capabilities=("editing",),
        constraints=(),
        acceptance_criteria=("Tests pass",),
        validation_commands=("python -m pytest",),
        architecture_constraints=(),
        evidence_references=(),
        estimated_risk=PlanningRisk.LOW,
        warnings=(),
    )


def test_feature_plan_contains_change_test_and_validation() -> None:
    steps = synthesize_steps(
        intent=PlanningIntent.IMPLEMENT_FEATURE,
        analysis=analysis(),
    )

    assert tuple(step.kind for step in steps) == (
        StepKind.ANALYSIS,
        StepKind.CODE_CHANGE,
        StepKind.TEST,
        StepKind.VALIDATION,
    )
'@

Write-Utf8NoBom "tests\test_autonomous_planning_dependency_synthesis.py" @'
from forge.autonomous_planning.analysis import (
    PlanningAnalysis,
)
from forge.autonomous_planning.dependency_synthesis import (
    synthesize_linear_dependencies,
)
from forge.autonomous_planning.states import (
    PlanningIntent,
    PlanningRisk,
)
from forge.autonomous_planning.step_synthesis import (
    synthesize_steps,
)


def test_dependencies_form_linear_chain() -> None:
    steps = synthesize_steps(
        intent=PlanningIntent.IMPLEMENT_FEATURE,
        analysis=PlanningAnalysis(
            objective="Implement feature",
            target_paths=(),
            required_capabilities=(),
            constraints=(),
            acceptance_criteria=(),
            validation_commands=(),
            architecture_constraints=(),
            evidence_references=(),
            estimated_risk=PlanningRisk.LOW,
            warnings=(),
        ),
    )

    dependencies = synthesize_linear_dependencies(steps)

    assert len(dependencies) == len(steps) - 1
    assert dependencies[0].source_step_id == (
        steps[1].step_id
    )
    assert dependencies[0].target_step_id == (
        steps[0].step_id
    )
'@

Write-Utf8NoBom "tests\test_autonomous_planning_plan_generation.py" @'
from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.models import PlanningRequest
from forge.autonomous_planning.plan_generation import (
    AutonomousPlanGenerator,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.states import (
    PlanningIntent,
    PlanningState,
)


def test_generator_builds_ready_plan() -> None:
    result = AutonomousPlanGenerator(
        policy=AutonomousPlanningPolicy()
    ).generate(
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
            validation_commands=(
                "python -m pytest",
            ),
        ),
    )

    assert result.plan.state is PlanningState.READY
    assert result.ordered_step_ids == tuple(
        step.step_id
        for step in result.plan.steps
    )


def test_high_risk_plan_requires_approval() -> None:
    result = AutonomousPlanGenerator(
        policy=AutonomousPlanningPolicy()
    ).generate(
        request=PlanningRequest(
            request_id="request-1",
            objective="Release production migration",
            repository_root="repository",
            intent=PlanningIntent.RELEASE,
            acceptance_criteria=("Release validated",),
            created_by="Aerion",
        ),
        context=PlanningContext(
            repository_root="repository",
            repository_fingerprint="fingerprint-1",
        ),
    )

    assert result.plan.requires_approval
    assert (
        result.plan.state
        is PlanningState.AWAITING_APPROVAL
    )
'@

Write-Host ""
Write-Host "M5.6 Package 2 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_planning_analysis.py `
    .\tests\test_autonomous_planning_step_synthesis.py `
    .\tests\test_autonomous_planning_dependency_synthesis.py `
    .\tests\test_autonomous_planning_plan_generation.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.6 Package 2 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.6 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short