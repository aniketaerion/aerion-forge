import pytest

from forge.autonomous_execution_v2.errors import ExecutionContractError
from forge.autonomous_execution_v2.models import (
    ExecutionDependency,
    ExecutionEvidence,
    ExecutionRequest,
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.states import EvidenceKind


def step(step_id: str, sequence: int) -> ExecutionStep:
    return ExecutionStep(
        step_id=step_id,
        planning_step_id=f"planning-{step_id}",
        sequence=sequence,
        name=f"Step {sequence}",
        description="Execute a repository-grounded action.",
    )


def test_request_rejects_empty_plan_id() -> None:
    with pytest.raises(ExecutionContractError):
        ExecutionRequest(
            request_id="request-1",
            plan_id="",
            plan_version=1,
            repository_root="repository",
            repository_fingerprint="fingerprint",
            requested_by="Aerion",
        )


def test_run_accepts_known_dependency() -> None:
    run = ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        steps=(
            step("step-1", 1),
            step("step-2", 2),
        ),
        dependencies=(
            ExecutionDependency(
                dependency_id="dependency-1",
                source_step_id="step-2",
                target_step_id="step-1",
                rationale="Step two requires step one.",
            ),
        ),
    )

    assert len(run.steps) == 2


def test_evidence_requires_references() -> None:
    with pytest.raises(ExecutionContractError):
        ExecutionEvidence(
            evidence_id="evidence-1",
            run_id="run-1",
            step_id="step-1",
            attempt_id="attempt-1",
            kind=EvidenceKind.TEST_RESULT,
            references=(),
            summary="Tests passed.",
        )