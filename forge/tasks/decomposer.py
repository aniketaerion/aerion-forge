"""Deterministic decomposition of Mission Plans into Task Sets."""

from forge.planning.models import (
    MissionPlan,
    MissionPlanningStatus,
)
from forge.tasks.builder import (
    build_child_task,
    build_parent_task,
)
from forge.tasks.errors import (
    TaskDefinitionError,
    TaskValidationError,
)
from forge.tasks.identifiers import (
    build_task_set_fingerprint,
)
from forge.tasks.models import (
    EngineeringTask,
    TaskManagementConfiguration,
    TaskSet,
)
from forge.tasks.validator import (
    calculate_statistics,
    validate_task_set,
)


def _validate_mission(
    mission: MissionPlan,
    configuration: TaskManagementConfiguration,
) -> None:
    if not configuration.enabled:
        raise TaskDefinitionError(
            "Task Management is disabled."
        )

    if not mission.workstreams:
        raise TaskDefinitionError(
            "Mission does not contain workstreams."
        )

    if (
        configuration.require_approved_mission
        and mission.status
        not in {
            MissionPlanningStatus.READY,
            MissionPlanningStatus.READY_WITH_CONDITIONS,
        }
    ):
        raise TaskDefinitionError(
            "Mission must be ready before task decomposition."
        )


def decompose_mission(
    mission: MissionPlan,
    configuration: TaskManagementConfiguration | None = None,
) -> TaskSet:
    """Convert one Mission Plan into a validated deterministic Task Set."""

    active = (
        configuration
        if configuration is not None
        else TaskManagementConfiguration()
    )
    _validate_mission(mission, active)

    workstreams = tuple(
        sorted(
            mission.workstreams,
            key=lambda item: item.workstream_id,
        )
    )
    workstream_ids = {
        workstream.workstream_id
        for workstream in workstreams
    }

    for workstream in workstreams:
        unknown = set(workstream.dependencies) - workstream_ids
        if unknown:
            raise TaskDefinitionError(
                "Workstream dependencies reference unknown IDs: "
                + ", ".join(sorted(unknown))
            )

    parent_ids: dict[str, str] = {}
    sequence = 1

    for workstream in workstreams:
        provisional = build_parent_task(
            mission=mission,
            workstream=workstream,
            sequence=sequence,
        )
        parent_ids[workstream.workstream_id] = provisional.task_id
        sequence += 1 + len(workstream.expected_outputs)

    tasks: list[EngineeringTask] = []
    sequence = 1

    for workstream in workstreams:
        dependency_ids = tuple(
            parent_ids[dependency]
            for dependency in sorted(workstream.dependencies)
        )
        parent = build_parent_task(
            mission=mission,
            workstream=workstream,
            sequence=sequence,
            dependency_task_ids=dependency_ids,
        )
        tasks.append(parent)
        sequence += 1

        outputs = tuple(
            sorted(
                workstream.expected_outputs,
                key=lambda value: value.casefold(),
            )
        )

        for output_index, output in enumerate(
            outputs,
            start=1,
        ):
            tasks.append(
                build_child_task(
                    mission=mission,
                    workstream=workstream,
                    parent_task=parent,
                    output=output,
                    sequence=sequence,
                    output_index=output_index,
                )
            )
            sequence += 1

    ordered = tuple(
        sorted(
            tasks,
            key=lambda item: (
                item.sequence,
                item.task_id,
            ),
        )
    )

    if len(ordered) > active.max_tasks_per_mission:
        raise TaskDefinitionError(
            "Decomposed task count exceeds configuration."
        )

    task_set = TaskSet(
        mission_id=mission.mission_id,
        mission_fingerprint=mission.mission_fingerprint,
        task_set_fingerprint="0" * 64,
        tasks=ordered,
        statistics=calculate_statistics(ordered),
        source_fingerprints={
            "mission": mission.mission_fingerprint,
            **dict(sorted(mission.source_fingerprints.items())),
        },
    )
    task_set = task_set.model_copy(
        update={
            "task_set_fingerprint":
                build_task_set_fingerprint(task_set)
        }
    )

    validation = validate_task_set(task_set, active)

    if not validation.valid:
        detail = "; ".join(
            message.message
            for message in validation.messages
        )
        raise TaskValidationError(detail)

    return task_set
