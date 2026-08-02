"""Atomic deterministic persistence for Task Management."""

import json
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from forge.tasks.errors import (
    TaskPersistenceError,
    TaskSchemaMismatchError,
    TaskStoreCorruptionError,
)
from forge.tasks.models import (
    SCHEMA_VERSION,
    TaskGeneration,
    TaskSet,
    TaskStore,
)


class TaskRepository:
    """Persist task sets without partial replacement."""

    def __init__(
        self,
        path: Path,
        history_limit: int = 5,
    ) -> None:
        if history_limit < 0:
            raise ValueError("history_limit cannot be negative.")

        self.path = path
        self.history_limit = history_limit

    def load(self) -> TaskStore:
        """Load and validate the task store."""

        if not self.path.exists():
            return TaskStore()

        try:
            raw = self.path.read_text(encoding="utf-8")
            payload = json.loads(raw)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise TaskStoreCorruptionError(
                "Persisted task state is unreadable."
            ) from exc

        if not isinstance(payload, dict):
            raise TaskStoreCorruptionError(
                "Persisted task state must be a JSON object."
            )

        schema_version = payload.get("schema_version")

        if schema_version != SCHEMA_VERSION:
            raise TaskSchemaMismatchError(
                "Unsupported task-store schema: "
                f"{schema_version!r}."
            )

        try:
            return TaskStore.model_validate(payload)
        except ValidationError as exc:
            raise TaskStoreCorruptionError(
                "Persisted task state violates the task-store contract."
            ) from exc

    def save(
        self,
        task_set: TaskSet,
        generation: TaskGeneration,
    ) -> TaskStore:
        """Atomically persist one mission task set."""

        if generation.mission_id != task_set.mission_id:
            raise TaskPersistenceError(
                "Generation mission does not match the task set."
            )

        if (
            generation.task_set_fingerprint
            != task_set.task_set_fingerprint
        ):
            raise TaskPersistenceError(
                "Generation fingerprint does not match the task set."
            )

        previous = self.load()

        tasks = dict(previous.tasks)
        history = {
            task_id: list(versions)
            for task_id, versions in previous.history.items()
        }
        generations = dict(previous.generations)

        incoming_ids = {
            task.task_id
            for task in task_set.tasks
        }

        previous_mission_ids = {
            task_id
            for task_id, task in tasks.items()
            if task.mission_id == task_set.mission_id
        }

        removed_ids = previous_mission_ids - incoming_ids

        for task_id in sorted(removed_ids):
            removed_task = tasks.pop(task_id)

            versions = history.setdefault(task_id, [])
            versions.append(removed_task)

            if self.history_limit == 0:
                history.pop(task_id, None)
            else:
                history[task_id] = versions[-self.history_limit :]

        for task in task_set.tasks:
            existing_task = tasks.get(task.task_id)

            if (
                existing_task is not None
                and existing_task.task_fingerprint != task.task_fingerprint
            ):
                versions = history.setdefault(task.task_id, [])
                versions.append(existing_task)

                if self.history_limit == 0:
                    history.pop(task.task_id, None)
                else:
                    history[task.task_id] = versions[
                        -self.history_limit :
                    ]

            tasks[task.task_id] = task

        generations[task_set.mission_id] = generation

        updated = TaskStore(
            tasks={
                task_id: tasks[task_id]
                for task_id in sorted(tasks)
            },
            history={
                task_id: history[task_id]
                for task_id in sorted(history)
                if history[task_id]
            },
            generations={
                mission_id: generations[mission_id]
                for mission_id in sorted(generations)
            },
        )

        content = (
            updated.model_dump_json(
                indent=2,
                exclude_none=False,
            )
            + "\n"
        ).encode("utf-8")

        self._atomic_write(content)
        return updated

    def snapshot_bytes(self) -> bytes | None:
        """Return current store bytes for rollback."""

        if not self.path.exists():
            return None

        try:
            return self.path.read_bytes()
        except OSError as exc:
            raise TaskPersistenceError(
                "Unable to snapshot the task store."
            ) from exc

    def restore_bytes(
        self,
        snapshot: bytes | None,
    ) -> None:
        """Restore a previous task-store snapshot."""

        if snapshot is None:
            try:
                self.path.unlink(missing_ok=True)
            except OSError as exc:
                raise TaskPersistenceError(
                    "Unable to remove the task store during rollback."
                ) from exc
            return

        self._atomic_write(snapshot)

    def probe_write(self) -> None:
        """Verify that the store directory supports atomic writes."""

        probe = b'{"probe":"task-store"}\n'
        directory = self.path.parent
        directory.mkdir(parents=True, exist_ok=True)

        temporary: Path | None = None

        try:
            descriptor, name = tempfile.mkstemp(
                prefix=".tasks-probe-",
                suffix=".tmp",
                dir=directory,
            )
            temporary = Path(name)

            with os.fdopen(descriptor, "wb") as stream:
                stream.write(probe)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            raise TaskPersistenceError(
                "Task-store write probe failed."
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def _atomic_write(self, content: bytes) -> None:
        """Write bytes using a same-directory atomic replacement."""

        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary: Path | None = None

        try:
            descriptor, name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            temporary = Path(name)

            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(temporary, self.path)
            temporary = None
        except OSError as exc:
            raise TaskPersistenceError(
                "Atomic task-store replacement failed."
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
