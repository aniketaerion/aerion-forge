"""Deterministic runtime task scheduler."""

from itertools import count
from typing import Any
from uuid import uuid4

from forge.runtime.task_queue import RuntimeTask, TaskCallable, TaskQueue


class Scheduler:
    """Create ordered runtime tasks and submit them to a queue."""

    def __init__(self, task_queue: TaskQueue) -> None:
        self.task_queue = task_queue
        self._sequence = count()

    def submit(
        self,
        operation: TaskCallable,
        *args: Any,
        priority: int = 100,
        task_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Schedule a callable and return its stable task identifier."""
        identifier = task_id or uuid4().hex
        self.task_queue.put(
            RuntimeTask(priority, next(self._sequence), identifier, operation, args, kwargs)
        )
        return identifier
