from datetime import timedelta

import pytest
from pydantic import ValidationError

from forge.autonomous_execution.models import (
    ExecutionLease,
    StepExecutionRecord,
    utc_now,
)
from forge.autonomous_execution.states import StepExecutionState


def test_execution_lease_requires_valid_time_order() -> None:
    acquired = utc_now()

    with pytest.raises(ValidationError):
        ExecutionLease(
            lease_id="lease-1",
            mission_id="mission-1",
            repository_root="repository",
            holder="runtime",
            acquired_at=acquired,
            expires_at=acquired - timedelta(seconds=1),
        )


def test_successful_execution_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        StepExecutionRecord(
            execution_id="execution-1",
            mission_id="mission-1",
            step_id="step-1",
            state=StepExecutionState.SUCCEEDED,
            completed_at=utc_now(),
        )