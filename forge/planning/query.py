"""Defensive, read-only mission-plan queries."""

from forge.planning.errors import MissionNotFoundError
from forge.planning.models import (
    MissionAcceptanceCriterion,
    MissionAffectedArea,
    MissionApprovalRequirement,
    MissionAssumption,
    MissionContextReference,
    MissionDeliverable,
    MissionObjective,
    MissionPlan,
    MissionPlanChangeSet,
    MissionPlanningStatus,
    MissionPlanStore,
    MissionPrerequisite,
    MissionQuestion,
    MissionRisk,
    MissionScopeItem,
    MissionValidationStrategy,
    MissionWorkstream,
)


class MissionPlanQuery:
    """Immutable query facade over persisted mission plans."""

    def __init__(self, store: MissionPlanStore) -> None:
        self._store = store.model_copy(deep=True)

    def get_mission(self, mission_id: str) -> MissionPlan:
        try:
            return self._store.missions[mission_id].model_copy(deep=True)
        except KeyError as exc:
            raise MissionNotFoundError(
                f"Mission not found: {mission_id}"
            ) from exc

    def list_missions(self) -> tuple[MissionPlan, ...]:
        return tuple(
            self.get_mission(mission_id)
            for mission_id in sorted(self._store.missions)
        )

    def get_latest_mission_for_target(
        self,
        target_identity: str,
    ) -> MissionPlan:
        matches = tuple(
            mission
            for mission in self.list_missions()
            if mission.target_identity == target_identity
        )
        if not matches:
            raise MissionNotFoundError(
                f"No mission found for target: {target_identity}"
            )
        return matches[-1].model_copy(deep=True)

    def get_objective(self, mission_id: str) -> MissionObjective:
        return self.get_mission(mission_id).objective.model_copy(deep=True)

    def get_scope(
        self,
        mission_id: str,
    ) -> tuple[MissionScopeItem, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).scope
        )

    def get_context(
        self,
        mission_id: str,
    ) -> tuple[MissionContextReference, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).context
        )

    def get_affected_areas(
        self,
        mission_id: str,
    ) -> tuple[MissionAffectedArea, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).affected_areas
        )

    def get_workstreams(
        self,
        mission_id: str,
    ) -> tuple[MissionWorkstream, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).workstreams
        )

    def get_deliverables(
        self,
        mission_id: str,
    ) -> tuple[MissionDeliverable, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).deliverables
        )

    def get_acceptance_criteria(
        self,
        mission_id: str,
    ) -> tuple[MissionAcceptanceCriterion, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).acceptance_criteria
        )

    def get_validation_strategy(
        self,
        mission_id: str,
    ) -> tuple[MissionValidationStrategy, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).validation_strategy
        )

    def get_prerequisites(
        self,
        mission_id: str,
    ) -> tuple[MissionPrerequisite, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).prerequisites
        )

    def get_blocking_prerequisites(
        self,
        mission_id: str,
    ) -> tuple[MissionPrerequisite, ...]:
        return tuple(
            prerequisite
            for prerequisite in self.get_prerequisites(mission_id)
            if prerequisite.blocking
            and prerequisite.status.value != "satisfied"
        )

    def get_risks(
        self,
        mission_id: str,
    ) -> tuple[MissionRisk, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).risks
        )

    def get_approvals(
        self,
        mission_id: str,
    ) -> tuple[MissionApprovalRequirement, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).approvals
        )

    def get_assumptions(
        self,
        mission_id: str,
    ) -> tuple[MissionAssumption, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).assumptions
        )

    def get_questions(
        self,
        mission_id: str,
    ) -> tuple[MissionQuestion, ...]:
        return tuple(
            item.model_copy(deep=True)
            for item in self.get_mission(mission_id).questions
        )

    def get_changes(
        self,
        mission_id: str,
    ) -> MissionPlanChangeSet:
        mission = self.get_mission(mission_id)
        return MissionPlanChangeSet(
            mission_id=mission.mission_id,
            changes=(),
        )

    def is_ready(self, mission_id: str) -> bool:
        return (
            self.get_mission(mission_id).status
            is MissionPlanningStatus.READY
        )

