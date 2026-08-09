"""Planning policy for M5.9 Package 3."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.models import EngineeringRequest, RelevantFile
from forge.general_engineering.states import EngineeringRisk


@dataclass(frozen=True)
class PlanningDecision:
    selected_paths: tuple[str, ...]
    aggregate_risk: EngineeringRisk
    rationale: str


def select_planning_targets(
    request: EngineeringRequest,
    relevant_files: tuple[RelevantFile, ...],
    *,
    max_files: int = 20,
) -> PlanningDecision:
    """Select bounded, evidence-backed targets for a change plan."""
    available = {item.path: item for item in relevant_files}

    if request.explicit_target_paths:
        missing = [path for path in request.explicit_target_paths if path not in available]
        if missing:
            raise ValueError(
                "Explicit target paths are not repository-grounded: "
                + ", ".join(sorted(missing))
            )
        selected = tuple(request.explicit_target_paths)
    else:
        selected = tuple(item.path for item in relevant_files[:max_files])

    forbidden = set(request.forbidden_paths)
    blocked = [path for path in selected if any(
        path == item or path.startswith(f"{item.rstrip('/')}/")
        for item in forbidden
    )]
    if blocked:
        raise ValueError(
            "Selected targets violate request forbidden paths: "
            + ", ".join(sorted(blocked))
        )

    count = len(selected)
    if count <= 2:
        risk = EngineeringRisk.LOW
    elif count <= 5:
        risk = EngineeringRisk.MEDIUM
    elif count <= 10:
        risk = EngineeringRisk.HIGH
    else:
        risk = EngineeringRisk.CRITICAL

    return PlanningDecision(
        selected_paths=selected,
        aggregate_risk=risk,
        rationale=(
            f"Selected {count} evidence-backed repository path(s) within "
            "the approved request scope."
        ),
    )