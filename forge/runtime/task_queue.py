"""Thread-safe task queue primitives for runtime orchestration."""

from collections.abc import Callable
from dataclasses import dataclass, field
from queue import Empty, PriorityQueue
from typing import Any

TaskCallable = Callable[..., Any]


@dataclass(order=True, frozen=True)
class RuntimeTask:
    """A prioritized, immutable unit of executable work."""

    priority: int
    sequence: int
    task_id: str = field(compare=False)
    operation: TaskCallable = field(compare=False)
    args: tuple[Any, ...] = field(default_factory=tuple, compare=False)
    kwargs: dict[str, Any] = field(default_factory=dict, compare=False)


class TaskQueue:
    """Coordinate prioritized runtime tasks between producers and workers."""

    def __init__(self) -> None:
        self._queue: PriorityQueue[RuntimeTask] = PriorityQueue()

    def put(self, task: RuntimeTask) -> None:
        """Add a task to the queue."""
        self._queue.put(task)

    def get(self, timeout: float | None = None) -> RuntimeTask | None:
        """Return the next task, or ``None`` when the timeout expires."""
        try:
            return self._queue.get(timeout=timeout)
        except Empty:
            return None

    def complete(self) -> None:
        """Mark the most recently retrieved task as complete."""
        self._queue.task_done()

    @property
    def pending(self) -> int:
        """Return the approximate number of queued tasks."""
        return self._queue.qsize()
