from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.repository import InMemoryExecutionRepository


def test_repository_persists_run() -> None:
    repository = InMemoryExecutionRepository()
    run = ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        steps=(
            ExecutionStep(
                step_id="step-1",
                planning_step_id="planning-step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
            ),
        ),
    )

    repository.put_run(run)

    assert repository.get_run("run-1") == run
    assert repository.all_runs() == (run,)