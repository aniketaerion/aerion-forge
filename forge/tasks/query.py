"""Immutable query facade for persisted Task Management state."""

from forge.tasks.errors import TaskNotFoundError
from forge.tasks.models import (
    EngineeringTask,
    TaskGeneration,
    TaskPriority,
    TaskRiskLevel,
    TaskStatistics,
    TaskStatus,
    TaskStore,
)


class TaskQuery:
    """Read-only deterministic queries over a task store."""

    def __init__(self, store: TaskStore) -> None:
        self._store = store.model_copy(deep=True)

    def get_task(self, task_id: str) -> EngineeringTask:
        """Return one task by ID."""

        try:
            return self._store.tasks[task_id].model_copy(deep=True)
        except KeyError as exc:
            raise TaskNotFoundError(
                f"Task was not found: {task_id}"
            ) from exc

    def list_tasks(self) -> tuple[EngineeringTask, ...]:
        """Return every task in deterministic order."""

        return tuple(
            self.get_task(task_id)
            for task_id in sorted(
                self._store.tasks,
                key=lambda task_id: (
                    self._store.tasks[task_id].sequence,
                    task_id,
                ),
            )
        )

    def list_tasks_for_mission(
        self,
        mission_id: str,
    ) -> tuple[EngineeringTask, ...]:
        """Return tasks for one mission."""

        return tuple(
            task
            for task in self.list_tasks()
            if task.mission_id == mission_id
        )

    def list_tasks_for_workstream(
        self,
        workstream_id: str,
    ) -> tuple[EngineeringTask, ...]:
        """Return tasks for one workstream."""

        return tuple(
            task
            for task in self.list_tasks()
            if task.workstream_id == workstream_id
        )

    def list_tasks_by_status(
        self,
        status: TaskStatus,
    ) -> tuple[EngineeringTask, ...]:
        return tuple(
            task
            for task in self.list_tasks()
            if task.status is status
        )

    def list_tasks_by_priority(
        self,
        priority: TaskPriority,
    ) -> tuple[EngineeringTask, ...]:
        return tuple(
            task
            for task in self.list_tasks()
            if task.priority is priority
        )

    def list_tasks_by_risk(
        self,
        risk: TaskRiskLevel,
    ) -> tuple[EngineeringTask, ...]:
        return tuple(
            task
            for task in self.list_tasks()
            if task.risk_level is risk
        )

    def list_blocked_tasks(self) -> tuple[EngineeringTask, ...]:
        return self.list_tasks_by_status(TaskStatus.BLOCKED)

    def list_ready_tasks(self) -> tuple[EngineeringTask, ...]:
        return self.list_tasks_by_status(TaskStatus.READY)

    def get_children(
        self,
        parent_task_id: str,
    ) -> tuple[EngineeringTask, ...]:
        self.get_task(parent_task_id)

        return tuple(
            task
            for task in self.list_tasks()
            if task.parent_task_id == parent_task_id
        )

    def get_parent(
        self,
        task_id: str,
    ) -> EngineeringTask | None:
        task = self.get_task(task_id)

        if task.parent_task_id is None:
            return None

        return self.get_task(task.parent_task_id)

    def get_dependencies(
        self,
        task_id: str,
    ) -> tuple[EngineeringTask, ...]:
        task = self.get_task(task_id)

        return tuple(
            self.get_task(dependency_id)
            for dependency_id in sorted(
                {
                    dependency.dependency_task_id
                    for dependency in task.dependencies
                }
            )
        )

    def get_dependents(
        self,
        task_id: str,
    ) -> tuple[EngineeringTask, ...]:
        self.get_task(task_id)

        return tuple(
            task
            for task in self.list_tasks()
            if any(
                dependency.dependency_task_id == task_id
                for dependency in task.dependencies
            )
        )

    def get_generation(
        self,
        mission_id: str,
    ) -> TaskGeneration:
        try:
            return self._store.generations[
                mission_id
            ].model_copy(deep=True)
        except KeyError as exc:
            raise TaskNotFoundError(
                "Task generation was not found for mission: "
                f"{mission_id}"
            ) from exc

    def get_statistics(
        self,
        mission_id: str,
    ) -> TaskStatistics:
        return self.get_generation(
            mission_id
        ).statistics.model_copy(deep=True)

    def is_complete(self, mission_id: str) -> bool:
        tasks = self.list_tasks_for_mission(mission_id)

        return bool(tasks) and all(
            task.status is TaskStatus.COMPLETED
            for task in tasks
        )
