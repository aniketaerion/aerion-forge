"""Bounded runtime execution loop."""

from collections.abc import Callable

from forge.runtime.worker import TaskOutcome, Worker


class ExecutionLoop:
    """Drain queued tasks while allowing callers to request shutdown."""

    def __init__(self, worker: Worker, should_stop: Callable[[], bool] | None = None) -> None:
        self.worker = worker
        self.should_stop = should_stop or (lambda: False)

    def drain(self) -> list[TaskOutcome]:
        """Run queued work until the queue is empty or shutdown is requested."""
        outcomes: list[TaskOutcome] = []
        while not self.should_stop():
            outcome = self.worker.run_once(timeout=0)
            if outcome is None:
                break
            outcomes.append(outcome)
        return outcomes
