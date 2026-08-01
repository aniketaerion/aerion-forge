"""Single-task runtime worker."""

from dataclasses import dataclass
from typing import Any

from forge.runtime.task_queue import TaskQueue


@dataclass(frozen=True)
class TaskOutcome:
    """Capture the result of one runtime task without hiding failures."""

    task_id: str
    result: Any = None
    error: Exception | None = None

    @property
    def succeeded(self) -> bool:
        """Return whether the task completed without an exception."""
        return self.error is None


class Worker:
    """Execute tasks retrieved from a shared queue."""

    def __init__(self, task_queue: TaskQueue) -> None:
        self.task_queue = task_queue

    def run_once(self, timeout: float | None = None) -> TaskOutcome | None:
        """Execute one available task and return its outcome."""
        task = self.task_queue.get(timeout)
        if task is None:
            return None
        try:
            return TaskOutcome(task.task_id, result=task.operation(*task.args, **task.kwargs))
        except Exception as exc:
            return TaskOutcome(task.task_id, error=exc)
        finally:
            self.task_queue.complete()
