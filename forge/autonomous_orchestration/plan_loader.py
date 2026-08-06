"""Approved-plan loading and version validation."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_orchestration.errors import (
    OrchestrationContractError,
)
from forge.autonomous_runtime.models import MissionPlan


@dataclass(slots=True)
class InMemoryApprovedPlanStore:
    """In-memory approved-plan store keyed by mission."""

    _plans: dict[str, MissionPlan] = field(default_factory=dict)

    def register(self, plan: MissionPlan) -> None:
        existing = self._plans.get(plan.mission_id)

        if existing is not None and existing.version >= plan.version:
            raise OrchestrationContractError(
                "Approved plan version must increase."
            )

        self._plans[plan.mission_id] = plan

    def load(
        self,
        mission_id: str,
        *,
        expected_plan_id: str,
        expected_version: int,
    ) -> MissionPlan:
        try:
            plan = self._plans[mission_id]
        except KeyError as exc:
            raise OrchestrationContractError(
                f"No approved plan exists for mission: {mission_id}"
            ) from exc

        if plan.plan_id != expected_plan_id:
            raise OrchestrationContractError(
                "Approved plan identifier mismatch."
            )

        if plan.version != expected_version:
            raise OrchestrationContractError(
                "Approved plan version mismatch."
            )

        return plan