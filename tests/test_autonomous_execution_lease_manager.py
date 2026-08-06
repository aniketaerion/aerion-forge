from datetime import UTC, datetime

import pytest

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_execution.lease_manager import (
    InMemoryExecutionLeaseManager,
)


def test_single_writer_lease_is_enforced() -> None:
    manager = InMemoryExecutionLeaseManager()
    now = datetime.now(UTC)

    manager.acquire(
        mission_id="mission-1",
        repository_root="repository",
        holder="runtime-1",
        lease_seconds=60,
        now=now,
    )

    with pytest.raises(ExecutionContractError):
        manager.acquire(
            mission_id="mission-2",
            repository_root="repository",
            holder="runtime-2",
            lease_seconds=60,
            now=now,
        )


def test_released_lease_allows_new_writer() -> None:
    manager = InMemoryExecutionLeaseManager()
    now = datetime.now(UTC)

    lease = manager.acquire(
        mission_id="mission-1",
        repository_root="repository",
        holder="runtime-1",
        lease_seconds=60,
        now=now,
    )
    manager.release(lease, now=now)

    next_lease = manager.acquire(
        mission_id="mission-2",
        repository_root="repository",
        holder="runtime-2",
        lease_seconds=60,
        now=now,
    )

    assert next_lease.mission_id == "mission-2"