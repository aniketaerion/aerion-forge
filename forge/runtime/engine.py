"""Composition root for platform runtime services."""

from typing import Any

from forge.runtime.execution_loop import ExecutionLoop
from forge.runtime.scheduler import Scheduler
from forge.runtime.task_queue import TaskCallable, TaskQueue
from forge.runtime.worker import TaskOutcome, Worker


class RuntimeEngine:
    """Expose a small synchronous API over scheduling and execution services."""

    def __init__(self) -> None:
        self.task_queue = TaskQueue()
        self.scheduler = Scheduler(self.task_queue)
        self.worker = Worker(self.task_queue)
        self.execution_loop = ExecutionLoop(self.worker)

    def submit(self, operation: TaskCallable, *args: Any, **kwargs: Any) -> str:
        """Submit a task for later execution."""
        return self.scheduler.submit(operation, *args, **kwargs)

    def run(self) -> list[TaskOutcome]:
        """Execute all currently queued tasks in priority order."""
        return self.execution_loop.drain()
