"""Deterministic identifiers for Safe Change Planning."""

import hashlib
import json
from collections.abc import Mapping, Sequence

from forge.safe_change_planning.models import (
    ChangeAction,
    ChangePhase,
    ChangeRequest,
    ChangeRiskAssessment,
    ChangeTarget,
    DependencyImpact,
    RiskFactor,
    RollbackStep,
    SafeChangePlan,
    VerificationStep,
)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _identifier(
    prefix: str,
    value: object,
) -> str:
    return f"{prefix}-{_digest(value)[:20]}"


def change_request_id(
    *,
    mission_id: str,
    task_ids: Sequence[str],
    objective: str,
    constraints: Sequence[str],
    requested_outcomes: Sequence[str],
    source_fingerprints: Mapping[str, str],
) -> str:
    return _identifier(
        "change-request",
        {
            "mission_id": mission_id.strip(),
            "task_ids": sorted(set(task_ids)),
            "objective": objective.strip(),
            "constraints": sorted(set(constraints)),
            "requested_outcomes": sorted(set(requested_outcomes)),
            "source_fingerprints": dict(sorted(source_fingerprints.items())),
        },
    )


def change_request_fingerprint(
    request: ChangeRequest,
) -> str:
    payload = request.model_dump(
        mode="json",
        exclude={"request_fingerprint"},
    )
    return _digest(payload)


def change_target_id(
    *,
    target_type: str,
    path: str,
    component: str,
) -> str:
    return _identifier(
        "change-target",
        {
            "target_type": target_type,
            "path": path.strip(),
            "component": component.strip(),
        },
    )


def change_action_id(
    *,
    request_id: str,
    target_id: str,
    action_type: str,
    description: str,
) -> str:
    return _identifier(
        "change-action",
        {
            "request_id": request_id,
            "target_id": target_id,
            "action_type": action_type,
            "description": description.strip(),
        },
    )


def dependency_impact_id(
    *,
    source_target_id: str,
    affected_target_id: str,
    dependency_type: str,
    depth: int,
) -> str:
    return _identifier(
        "dependency-impact",
        {
            "source_target_id": source_target_id,
            "affected_target_id": affected_target_id,
            "dependency_type": dependency_type,
            "depth": depth,
        },
    )


def risk_factor_id(
    *,
    factor_type: str,
    reason: str,
    source_ids: Sequence[str],
) -> str:
    return _identifier(
        "risk-factor",
        {
            "factor_type": factor_type,
            "reason": reason.strip(),
            "source_ids": sorted(set(source_ids)),
        },
    )


def risk_assessment_id(
    *,
    request_id: str,
    factors: Sequence[RiskFactor],
) -> str:
    return _identifier(
        "risk-assessment",
        {
            "request_id": request_id,
            "factor_ids": sorted(factor.factor_id for factor in factors),
        },
    )


def verification_step_id(
    *,
    request_id: str,
    verification_type: str,
    description: str,
    target_ids: Sequence[str],
) -> str:
    return _identifier(
        "verification-step",
        {
            "request_id": request_id,
            "verification_type": verification_type,
            "description": description.strip(),
            "target_ids": sorted(set(target_ids)),
        },
    )


def rollback_step_id(
    *,
    request_id: str,
    description: str,
    target_ids: Sequence[str],
) -> str:
    return _identifier(
        "rollback-step",
        {
            "request_id": request_id,
            "description": description.strip(),
            "target_ids": sorted(set(target_ids)),
        },
    )


def change_phase_id(
    *,
    request_id: str,
    phase_type: str,
    sequence: int,
    action_ids: Sequence[str],
) -> str:
    return _identifier(
        "change-phase",
        {
            "request_id": request_id,
            "phase_type": phase_type,
            "sequence": sequence,
            "action_ids": sorted(set(action_ids)),
        },
    )


def safe_change_plan_id(
    *,
    request: ChangeRequest,
    targets: Sequence[ChangeTarget],
    actions: Sequence[ChangeAction],
    dependencies: Sequence[DependencyImpact],
    risk_assessment: ChangeRiskAssessment,
    verification_steps: Sequence[VerificationStep],
    rollback_steps: Sequence[RollbackStep],
    phases: Sequence[ChangePhase],
) -> str:
    return _identifier(
        "safe-change-plan",
        {
            "request_id": request.request_id,
            "request_fingerprint": (request.request_fingerprint),
            "target_ids": sorted(target.target_id for target in targets),
            "action_ids": sorted(action.action_id for action in actions),
            "dependency_ids": sorted(dependency.dependency_id for dependency in dependencies),
            "risk_assessment_id": (risk_assessment.assessment_id),
            "verification_ids": sorted(step.step_id for step in verification_steps),
            "rollback_ids": sorted(step.step_id for step in rollback_steps),
            "phase_ids": sorted(phase.phase_id for phase in phases),
        },
    )


def safe_change_plan_fingerprint(
    plan: SafeChangePlan,
) -> str:
    payload = plan.model_dump(
        mode="json",
        exclude={"plan_fingerprint"},
    )
    return _digest(payload)


def change_target_fingerprint(
    target: ChangeTarget,
) -> str:
    return _digest(target.model_dump(mode="json"))


def change_action_fingerprint(
    action: ChangeAction,
) -> str:
    return _digest(action.model_dump(mode="json"))


def dependency_impact_fingerprint(
    dependency: DependencyImpact,
) -> str:
    return _digest(dependency.model_dump(mode="json"))
