import pytest

from forge.autonomous_decision.decision_journal import (
    InMemoryDecisionJournal,
)
from forge.autonomous_decision.errors import DecisionContractError
from forge.autonomous_decision.models import DecisionRecord
from forge.autonomous_decision.states import (
    DecisionDisposition,
    DecisionKind,
)


def record() -> DecisionRecord:
    return DecisionRecord(
        decision_id="decision-1",
        request_id="request-1",
        context_id="context-1",
        decision_kind=DecisionKind.STOP,
        disposition=DecisionDisposition.NO_SAFE_ACTION,
        rationale="No safe action.",
        confidence=0.0,
        context_fingerprint="fingerprint-1",
    )


def test_journal_is_append_only() -> None:
    journal = InMemoryDecisionJournal()
    journal.append(record())

    assert len(journal.all_records()) == 1

    with pytest.raises(DecisionContractError):
        journal.append(record())