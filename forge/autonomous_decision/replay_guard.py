"""Context-bound decision replay protection."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_decision.errors import DecisionReplayError
from forge.autonomous_decision.models import DecisionRecord


@dataclass(slots=True)
class DecisionReplayGuard:
    """Prevent conflicting committed decisions for one context."""

    _records_by_fingerprint: dict[str, DecisionRecord] = field(
        default_factory=dict
    )

    def check_and_record(
        self,
        record: DecisionRecord,
    ) -> DecisionRecord:
        """Accept identical replay and reject conflicting replay."""
        existing = self._records_by_fingerprint.get(
            record.context_fingerprint
        )

        if existing is None:
            self._records_by_fingerprint[
                record.context_fingerprint
            ] = record
            return record

        if existing == record:
            return existing

        raise DecisionReplayError(
            "Conflicting committed decision for context "
            f"{record.context_fingerprint}."
        )

    def get(
        self,
        context_fingerprint: str,
    ) -> DecisionRecord | None:
        return self._records_by_fingerprint.get(
            context_fingerprint
        )