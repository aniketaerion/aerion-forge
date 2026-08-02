"""Task Management orchestration without task execution."""

from pathlib import Path

from forge.planning.models import MissionPlan
from forge.tasks.decomposer import decompose_mission
from forge.tasks.errors import (
    TaskManagementDisabledError,
    TaskReportError,
    TaskValidationError,
)
from forge.tasks.models import (
    EngineeringTask,
    TaskChange,
    TaskChangeSet,
    TaskChangeType,
    TaskGeneration,
    TaskManagementConfiguration,
    TaskResult,
    TaskSet,
)
from forge.tasks.renderer import TaskRenderer
from forge.tasks.store import TaskRepository
from forge.tasks.validator import validate_task_set


class TaskManagementService:
    """Decompose, validate, persist and report engineering tasks."""

    def __init__(
        self,
        memory_path: Path,
        reports_path: Path,
        configuration: TaskManagementConfiguration | None = None,
        repository: TaskRepository | None = None,
        renderer: TaskRenderer | None = None,
    ) -> None:
        self.memory_path = memory_path
        self.reports_path = reports_path
        self.configuration = (
            configuration
            if configuration is not None
            else TaskManagementConfiguration()
        )
        self.repository = (
            repository
            if repository is not None
            else TaskRepository(
                memory_path / "tasks.json",
                history_limit=self.configuration.history_limit,
            )
        )
        self.renderer = (
            renderer
            if renderer is not None
            else TaskRenderer()
        )

    def build(
        self,
        mission: MissionPlan,
        *,
        persist: bool = True,
        write_reports: bool = True,
    ) -> TaskResult:
        """Build a deterministic task set from one mission."""

        if not self.configuration.enabled:
            raise TaskManagementDisabledError(
                "Task Management is disabled."
            )

        task_set = decompose_mission(
            mission,
            self.configuration,
        )

        validation = validate_task_set(
            task_set,
            self.configuration,
        )

        if not validation.valid:
            detail = "; ".join(
                message.message
                for message in validation.messages
            )
            raise TaskValidationError(detail)

        previous_tasks = self._previous_tasks(
            task_set,
            persist=persist,
        )
        changes = self._changes(
            task_set,
            previous_tasks,
        )
        generation = self._generation(
            task_set,
            previous_tasks,
        )

        store_snapshot = (
            self.repository.snapshot_bytes()
            if persist
            else None
        )
        report_snapshots: dict[str, bytes | None] = {}

        if write_reports:
            report_snapshots = self._snapshot_reports(
                TaskRenderer.REPORT_NAMES
            )

        try:
            if persist:
                self.repository.save(
                    task_set,
                    generation,
                )

            report_paths: tuple[str, ...] = ()

            if write_reports:
                reports = self.renderer.render(
                    task_set,
                    generation,
                    changes,
                )
                report_paths = self.renderer.write(
                    self.reports_path,
                    reports,
                )

        except Exception:
            if persist:
                self.repository.restore_bytes(
                    store_snapshot
                )

            if write_reports:
                self._restore_reports(
                    report_snapshots
                )

            raise

        return TaskResult(
            tasks=task_set.tasks,
            generation=generation,
            changes=changes,
            report_paths=report_paths,
        )

    def _previous_tasks(
        self,
        task_set: TaskSet,
        *,
        persist: bool,
    ) -> dict[str, EngineeringTask]:
        if not persist:
            return {}

        store = self.repository.load()

        return {
            task_id: task
            for task_id, task in store.tasks.items()
            if task.mission_id == task_set.mission_id
        }

    def _changes(
        self,
        task_set: TaskSet,
        previous: dict[str, EngineeringTask],
    ) -> TaskChangeSet:
        changes: list[TaskChange] = []
        current = {
            task.task_id: task
            for task in task_set.tasks
        }

        all_ids = sorted(
            set(previous) | set(current)
        )

        for task_id in all_ids:
            old = previous.get(task_id)
            new = current.get(task_id)

            if old is None and new is not None:
                change_type = TaskChangeType.CREATED
            elif old is not None and new is None:
                change_type = TaskChangeType.SUPERSEDED
            elif (
                old is not None
                and new is not None
                and old.task_fingerprint
                == new.task_fingerprint
            ):
                change_type = TaskChangeType.UNCHANGED
            else:
                change_type = TaskChangeType.UPDATED

            changes.append(
                TaskChange(
                    task_id=task_id,
                    field="task",
                    change_type=change_type,
                )
            )

        return TaskChangeSet(
            mission_id=task_set.mission_id,
            changes=tuple(changes),
        )

    def _generation(
        self,
        task_set: TaskSet,
        previous: dict[str, EngineeringTask],
    ) -> TaskGeneration:
        previous_generation_id: str | None = None

        if previous:
            previous_store = self.repository.load()
            previous_generation = (
                previous_store.generations.get(
                    task_set.mission_id
                )
            )

            if (
                previous_generation is not None
                and previous_generation.task_set_fingerprint
                != task_set.task_set_fingerprint
            ):
                previous_generation_id = (
                    previous_generation.generation_id
                )

        return TaskGeneration(
            generation_id=(
                "task-generation-"
                f"{task_set.task_set_fingerprint[:20]}"
            ),
            previous_generation_id=previous_generation_id,
            mission_id=task_set.mission_id,
            mission_fingerprint=task_set.mission_fingerprint,
            task_set_fingerprint=task_set.task_set_fingerprint,
            task_count=len(task_set.tasks),
            statistics=task_set.statistics,
        )

    def _snapshot_reports(
        self,
        report_names: tuple[str, ...],
    ) -> dict[str, bytes | None]:
        snapshots: dict[str, bytes | None] = {}

        for name in report_names:
            path = self.reports_path / name
            snapshots[name] = (
                path.read_bytes()
                if path.exists()
                else None
            )

        return snapshots

    def _restore_reports(
        self,
        snapshots: dict[str, bytes | None],
    ) -> None:
        self.reports_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        for name, content in snapshots.items():
            path = self.reports_path / name

            if content is None:
                path.unlink(missing_ok=True)
            else:
                try:
                    path.write_bytes(content)
                except OSError as exc:
                    raise TaskReportError(
                        "Unable to restore task report: "
                        f"{name}"
                    ) from exc
