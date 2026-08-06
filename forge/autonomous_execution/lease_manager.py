"""Single-writer execution lease management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from forge.autonomous_execution.errors import ExecutionContractError
from forge.autonomous_execution.identifiers import (
    execution_lease_identifier,
)
from forge.autonomous_execution.models import ExecutionLease


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class InMemoryExecutionLeaseManager:
    """Single-writer repository lease manager."""

    _leases: dict[str, ExecutionLease] = field(default_factory=dict)

    def acquire(
        self,
        *,
        mission_id: str,
        repository_root: str,
        holder: str,
        lease_seconds: int,
        now: datetime | None = None,
    ) -> ExecutionLease:
        moment = now or utc_now()
        active = self._leases.get(repository_root)

        if (
            active is not None
            and active.released_at is None
            and active.expires_at > moment
        ):
            raise ExecutionContractError(
                "Repository already has an active execution lease."
            )

        payload = {
            "mission_id": mission_id,
            "repository_root": repository_root,
            "holder": holder,
            "acquired_at": moment.isoformat(),
        }
        lease = ExecutionLease(
            lease_id=execution_lease_identifier(payload),
            mission_id=mission_id,
            repository_root=repository_root,
            holder=holder,
            acquired_at=moment,
            expires_at=moment + timedelta(seconds=lease_seconds),
        )
        self._leases[repository_root] = lease
        return lease

    def release(
        self,
        lease: ExecutionLease,
        *,
        now: datetime | None = None,
    ) -> ExecutionLease:
        moment = now or utc_now()
        current = self._leases.get(lease.repository_root)

        if current is None or current.lease_id != lease.lease_id:
            raise ExecutionContractError(
                "Execution lease is not active."
            )

        released = lease.model_copy(
            update={
                "released_at": moment,
                "version": lease.version + 1,
            }
        )
        self._leases[lease.repository_root] = released
        return released