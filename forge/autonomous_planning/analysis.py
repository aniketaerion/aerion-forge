"""Planning request analysis."""

from __future__ import annotations

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