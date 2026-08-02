"""Deterministic construction of engineering tasks from mission workstreams."""

from collections.abc import Iterable

from forge.planning.models import (
    MissionAcceptanceCriterion,
    MissionApprovalLevel,
    MissionContextReference,
    MissionPlan,
    MissionRiskLevel,
    MissionValidationCategory,
    MissionValidationStrategy,
    MissionWorkstream,
)
from forge.tasks.identifiers import (
    build_task_fingerprint,
    build_task_id,
)
from forge.tasks.models import (
    EngineeringTask,
    TaskAcceptanceCriterion,
    TaskApprovalLevel,
    TaskApprovalRequirement,
    TaskDependency,
    TaskDependencyType,
    TaskPriority,
    TaskRiskLevel,
    TaskSourceReference,
    TaskStatus,
    TaskValidationCategory,
    TaskValidationRequirement,
)


def _task_risk(level: MissionRiskLevel) -> TaskRiskLevel:
    return TaskRiskLevel(level.value)


def _task_priority(level: TaskRiskLevel) -> TaskPriority:
    mapping = {
        TaskRiskLevel.CRITICAL: TaskPriority.CRITICAL,
        TaskRiskLevel.HIGH: TaskPriority.HIGH,
        TaskRiskLevel.MEDIUM: TaskPriority.MEDIUM,
        TaskRiskLevel.LOW: TaskPriority.LOW,
        TaskRiskLevel.UNKNOWN: TaskPriority.MEDIUM,
    }
    return mapping[level]


def _approval_level(
    level: MissionApprovalLevel,
) -> TaskApprovalLevel:
    return TaskApprovalLevel(level.value)


def _validation_category(
    category: MissionValidationCategory,
) -> TaskValidationCategory:
    return TaskValidationCategory(category.value)


def build_acceptance_criteria(
    workstream: MissionWorkstream,
    mission_criteria: tuple[MissionAcceptanceCriterion, ...],
) -> tuple[TaskAcceptanceCriterion, ...]:
    """Build deterministic acceptance criteria for one workstream."""

    values: list[TaskAcceptanceCriterion] = []

    for index, statement in enumerate(
        workstream.completion_criteria,
        start=1,
    ):
        values.append(
            TaskAcceptanceCriterion(
                criterion_id=(
                    f"{workstream.workstream_id}-criterion-{index:03d}"
                ),
                statement=statement,
                mandatory=True,
                inherited_from_mission=False,
            )
        )

    for criterion in mission_criteria:
        values.append(
            TaskAcceptanceCriterion(
                criterion_id=criterion.criterion_id,
                statement=criterion.statement,
                mandatory=True,
                inherited_from_mission=True,
            )
        )

    if not values:
        values.append(
            TaskAcceptanceCriterion(
                criterion_id=(
                    f"{workstream.workstream_id}-criterion-default"
                ),
                statement=(
                    "The workstream objective and declared output "
                    "are verified as complete."
                ),
                mandatory=True,
                inherited_from_mission=False,
            )
        )

    return tuple(
        sorted(
            values,
            key=lambda item: item.criterion_id,
        )
    )


def build_validation_requirements(
    strategies: tuple[MissionValidationStrategy, ...],
    workstream_id: str,
) -> tuple[TaskValidationRequirement, ...]:
    """Build deterministic task validation requirements."""

    values = tuple(
        TaskValidationRequirement(
            requirement_id=strategy.strategy_id,
            category=_validation_category(strategy.category),
            description=strategy.description,
            mandatory=True,
            inherited_from_mission=True,
        )
        for strategy in strategies
    )

    if values:
        return tuple(
            sorted(
                values,
                key=lambda item: item.requirement_id,
            )
        )

    return (
        TaskValidationRequirement(
            requirement_id=f"{workstream_id}-manual-review",
            category=TaskValidationCategory.MANUAL_REVIEW,
            description=(
                "Review the completed task against its acceptance criteria."
            ),
            mandatory=True,
            inherited_from_mission=False,
        ),
    )


def build_approval_requirements(
    workstream: MissionWorkstream,
    mission: MissionPlan,
) -> tuple[TaskApprovalRequirement, ...]:
    """Build deduplicated approval requirements."""

    requirements: dict[
        TaskApprovalLevel,
        TaskApprovalRequirement,
    ] = {}

    for approval in mission.approvals:
        level = _approval_level(approval.level)
        requirements[level] = TaskApprovalRequirement(
            approval_id=approval.approval_id,
            level=level,
            reason=approval.reason,
            inherited_from_mission=True,
        )

    for level_value in workstream.required_approvals:
        level = _approval_level(level_value)
        requirements[level] = TaskApprovalRequirement(
            approval_id=(
                f"{workstream.workstream_id}-approval-{level.value}"
            ),
            level=level,
            reason=(
                f"{level.value.replace('_', ' ').title()} "
                "is required by the mission workstream."
            ),
            inherited_from_mission=True,
        )

    return tuple(
        requirements[level]
        for level in sorted(
            requirements,
            key=lambda item: item.value,
        )
    )


def build_source_references(
    references: tuple[MissionContextReference, ...],
) -> tuple[TaskSourceReference, ...]:
    """Map mission context into task source references."""

    return tuple(
        sorted(
            (
                TaskSourceReference(
                    reference_id=reference.entity_id,
                    reference_type=reference.entity_type,
                    canonical_name=reference.canonical_name,
                    evidence=reference.evidence,
                )
                for reference in references
            ),
            key=lambda item: (
                item.reference_type,
                item.canonical_name.casefold(),
                item.reference_id,
            ),
        )
    )


def _finalize_task(task: EngineeringTask) -> EngineeringTask:
    return task.model_copy(
        update={
            "task_fingerprint": build_task_fingerprint(task),
        }
    )


def build_parent_task(
    *,
    mission: MissionPlan,
    workstream: MissionWorkstream,
    sequence: int,
    dependency_task_ids: Iterable[str] = (),
) -> EngineeringTask:
    """Create one deterministic parent task for a workstream."""

    task_id = build_task_id(
        mission_id=mission.mission_id,
        workstream_id=workstream.workstream_id,
        parent_task_id=None,
        title=workstream.name,
        sequence=sequence,
    )
    risk = _task_risk(workstream.risk_level)

    dependencies = tuple(
        TaskDependency(
            task_id=task_id,
            dependency_task_id=dependency_task_id,
            dependency_type=TaskDependencyType.REQUIRES,
            blocking=True,
            reason="Required predecessor workstream.",
        )
        for dependency_task_id in sorted(set(dependency_task_ids))
    )

    task = EngineeringTask(
        task_id=task_id,
        task_fingerprint="0" * 64,
        mission_id=mission.mission_id,
        workstream_id=workstream.workstream_id,
        title=workstream.name,
        description=workstream.objective,
        status=TaskStatus.DRAFT,
        priority=_task_priority(risk),
        risk_level=risk,
        dependencies=dependencies,
        acceptance_criteria=build_acceptance_criteria(
            workstream,
            mission.acceptance_criteria,
        ),
        validation_requirements=build_validation_requirements(
            mission.validation_strategy,
            workstream.workstream_id,
        ),
        approval_requirements=build_approval_requirements(
            workstream,
            mission,
        ),
        source_references=build_source_references(mission.context),
        tags=("parent", "workstream"),
        sequence=sequence,
    )
    return _finalize_task(task)


def build_child_task(
    *,
    mission: MissionPlan,
    workstream: MissionWorkstream,
    parent_task: EngineeringTask,
    output: str,
    sequence: int,
    output_index: int,
) -> EngineeringTask:
    """Create one deterministic child task from one expected output."""

    title = f"Produce {output}"
    task_id = build_task_id(
        mission_id=mission.mission_id,
        workstream_id=workstream.workstream_id,
        parent_task_id=parent_task.task_id,
        title=title,
        sequence=sequence,
    )
    risk = _task_risk(workstream.risk_level)

    task = EngineeringTask(
        task_id=task_id,
        task_fingerprint="0" * 64,
        mission_id=mission.mission_id,
        workstream_id=workstream.workstream_id,
        parent_task_id=parent_task.task_id,
        title=title,
        description=(
            f"Produce the declared workstream output: {output}."
        ),
        status=TaskStatus.DRAFT,
        priority=_task_priority(risk),
        risk_level=risk,
        dependencies=(),
        acceptance_criteria=(
            TaskAcceptanceCriterion(
                criterion_id=(
                    f"{workstream.workstream_id}"
                    f"-output-{output_index:03d}"
                ),
                statement=(
                    f"The declared output '{output}' is complete "
                    "and satisfies the workstream objective."
                ),
                mandatory=True,
                inherited_from_mission=False,
            ),
        ),
        validation_requirements=build_validation_requirements(
            mission.validation_strategy,
            workstream.workstream_id,
        ),
        approval_requirements=build_approval_requirements(
            workstream,
            mission,
        ),
        source_references=build_source_references(mission.context),
        tags=("child", "expected-output"),
        sequence=sequence,
    )
    return _finalize_task(task)
