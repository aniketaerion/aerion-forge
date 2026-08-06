"""Append-only decision journal."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_decision.errors import DecisionContractError
from forge.autonomous_decision.models import DecisionRecord


@dataclass(slots=True)
class InMemoryDecisionJournal:
    """Deterministic append-only journal for committed decisions."""

    _records: list[DecisionRecord] = field(default_factory=list)

    def append(self, record: DecisionRecord) -> None:
        if any(
            existing.decision_id == record.decision_id
            for existing in self._records
        ):
            raise DecisionContractError(
                f"Duplicate decision record: {record.decision_id}"
            )

        self._records.append(record)

    def records_for_request(
        self,
        request_id: str,
    ) -> tuple[DecisionRecord, ...]:
        return tuple(
            record
            for record in self._records
            if record.request_id == request_id
        )

    def all_records(self) -> tuple[DecisionRecord, ...]:
        return tuple(self._records)