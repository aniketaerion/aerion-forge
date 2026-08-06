"""Deterministic planning-step synthesis."""

from __future__ import annotations

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