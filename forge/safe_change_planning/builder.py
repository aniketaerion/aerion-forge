"""Safe Change Planning deterministic builder."""

from collections.abc import Mapping, Sequence

from forge.safe_change_planning.identifiers import (
    change_action_id,
    change_phase_id,
    change_request_fingerprint,
    change_request_id,
    change_target_id,
    rollback_step_id,
    safe_change_plan_fingerprint,
    safe_change_plan_id,
    verification_step_id,
)
from forge.safe_change_planning.models import (
    ChangeAction,
    ChangeActionType,
    ChangePhase,
    ChangePlanningConfiguration,
    ChangeRequest,
    ChangeTarget,
    ChangeTargetType,
    DependencyImpact,
    PlanningPhaseType,
    PlanStatistics,
    RollbackStep,
    SafeChangePlan,
    VerificationStep,
    VerificationType,
)
from forge.safe_change_planning.policies import (
    build_risk_assessment,
)


class SafeChangePlanningBuilder:
    """Build deterministic Safe Change Planning artifacts."""

    def build_request(
        self,
        *,
        mission_id: str,
        task_ids: Sequence[str],
        objective: str,
        constraints: Sequence[str] = (),
        requested_outcomes: Sequence[str] = (),
        source_fingerprints: Mapping[str, str] | None = None,
    ) -> ChangeRequest:
        fingerprints = dict(sorted((source_fingerprints or {}).items()))

        request_id = change_request_id(
            mission_id=mission_id,
            task_ids=task_ids,
            objective=objective,
            constraints=constraints,
            requested_outcomes=requested_outcomes,
            source_fingerprints=fingerprints,
        )

        provisional = ChangeRequest(
            request_id=request_id,
            request_fingerprint="pending",
            mission_id=mission_id,
            task_ids=tuple(task_ids),
            objective=objective,
            constraints=tuple(constraints),
            requested_outcomes=tuple(requested_outcomes),
            source_fingerprints=fingerprints,
        )

        return provisional.model_copy(
            update={"request_fingerprint": (change_request_fingerprint(provisional))}
        )

    def build_target(
        self,
        *,
        target_type: ChangeTargetType,
        path: str,
        component: str,
        reason: str,
        source_ids: Sequence[str] = (),
        metadata: Mapping[str, str] | None = None,
    ) -> ChangeTarget:
        return ChangeTarget(
            target_id=change_target_id(
                target_type=target_type.value,
                path=path,
                component=component,
            ),
            target_type=target_type,
            path=path,
            component=component,
            reason=reason,
            source_ids=tuple(source_ids),
            metadata=dict(metadata or {}),
        )

    def build_verification_step(
        self,
        *,
        request_id: str,
        verification_type: VerificationType,
        description: str,
        target_ids: Sequence[str],
        command: str | None = None,
        required: bool = True,
    ) -> VerificationStep:
        return VerificationStep(
            step_id=verification_step_id(
                request_id=request_id,
                verification_type=verification_type.value,
                description=description,
                target_ids=target_ids,
            ),
            verification_type=verification_type,
            description=description,
            target_ids=tuple(target_ids),
            command=command,
            required=required,
        )

    def build_rollback_step(
        self,
        *,
        request_id: str,
        description: str,
        target_ids: Sequence[str],
        irreversible: bool = False,
        limitation: str | None = None,
    ) -> RollbackStep:
        return RollbackStep(
            step_id=rollback_step_id(
                request_id=request_id,
                description=description,
                target_ids=target_ids,
            ),
            description=description,
            target_ids=tuple(target_ids),
            irreversible=irreversible,
            limitation=limitation,
        )

    def build_action(
        self,
        *,
        request_id: str,
        target_id: str,
        action_type: ChangeActionType,
        description: str,
        prerequisites: Sequence[str] = (),
        verification_step_ids: Sequence[str] = (),
        rollback_step_ids: Sequence[str] = (),
        destructive: bool = False,
        mutating: bool = True,
    ) -> ChangeAction:
        return ChangeAction(
            action_id=change_action_id(
                request_id=request_id,
                target_id=target_id,
                action_type=action_type.value,
                description=description,
            ),
            target_id=target_id,
            action_type=action_type,
            description=description,
            prerequisites=tuple(prerequisites),
            verification_step_ids=tuple(verification_step_ids),
            rollback_step_ids=tuple(rollback_step_ids),
            destructive=destructive,
            mutating=mutating,
        )

    def build_phase(
        self,
        *,
        request_id: str,
        phase_type: PlanningPhaseType,
        sequence: int,
        title: str,
        action_ids: Sequence[str],
    ) -> ChangePhase:
        return ChangePhase(
            phase_id=change_phase_id(
                request_id=request_id,
                phase_type=phase_type.value,
                sequence=sequence,
                action_ids=action_ids,
            ),
            phase_type=phase_type,
            sequence=sequence,
            title=title,
            action_ids=tuple(action_ids),
        )

    def build_plan(
        self,
        *,
        request: ChangeRequest,
        targets: Sequence[ChangeTarget],
        actions: Sequence[ChangeAction],
        dependencies: Sequence[DependencyImpact],
        verification_steps: Sequence[VerificationStep],
        rollback_steps: Sequence[RollbackStep],
        phases: Sequence[ChangePhase],
        source_fingerprints: Mapping[str, str],
        configuration: ChangePlanningConfiguration,
    ) -> SafeChangePlan:
        ordered_targets = tuple(
            sorted(
                targets,
                key=lambda item: item.target_id,
            )
        )
        ordered_actions = tuple(
            sorted(
                actions,
                key=lambda item: item.action_id,
            )
        )
        ordered_dependencies = tuple(
            sorted(
                dependencies,
                key=lambda item: item.dependency_id,
            )
        )
        ordered_verification = tuple(
            sorted(
                verification_steps,
                key=lambda item: item.step_id,
            )
        )
        ordered_rollback = tuple(
            sorted(
                rollback_steps,
                key=lambda item: item.step_id,
            )
        )
        ordered_phases = tuple(
            sorted(
                phases,
                key=lambda item: (
                    item.sequence,
                    item.phase_id,
                ),
            )
        )

        risk_assessment = build_risk_assessment(
            request_id=request.request_id,
            targets=ordered_targets,
            actions=ordered_actions,
            dependencies=ordered_dependencies,
            configuration=configuration,
        )

        plan_id = safe_change_plan_id(
            request=request,
            targets=ordered_targets,
            actions=ordered_actions,
            dependencies=ordered_dependencies,
            risk_assessment=risk_assessment,
            verification_steps=ordered_verification,
            rollback_steps=ordered_rollback,
            phases=ordered_phases,
        )

        statistics = PlanStatistics(
            target_count=len(ordered_targets),
            action_count=len(ordered_actions),
            dependency_count=len(ordered_dependencies),
            verification_count=len(ordered_verification),
            rollback_count=len(ordered_rollback),
            phase_count=len(ordered_phases),
            high_risk_factor_count=sum(factor.score >= 70 for factor in risk_assessment.factors),
        )

        provisional = SafeChangePlan(
            plan_id=plan_id,
            plan_fingerprint="pending",
            request=request,
            targets=ordered_targets,
            actions=ordered_actions,
            dependencies=ordered_dependencies,
            risk_assessment=risk_assessment,
            verification_steps=ordered_verification,
            rollback_steps=ordered_rollback,
            phases=ordered_phases,
            statistics=statistics,
            source_fingerprints=dict(source_fingerprints),
        )

        return provisional.model_copy(
            update={"plan_fingerprint": (safe_change_plan_fingerprint(provisional))}
        )
