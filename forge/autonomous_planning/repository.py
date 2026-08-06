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