from forge.autonomous_decision.models import DecisionContext
from forge.autonomous_decision.rationale import build_rationale
from forge.autonomous_decision.states import DecisionDisposition


def test_no_safe_action_rationale_is_explicit() -> None:
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        authority_level="a1_read",
        approval_state="pending",
        repository_fingerprint="fingerprint-1",
        policy_version="1.0",
    )

    rationale = build_rationale(
        context=context,
        disposition=DecisionDisposition.NO_SAFE_ACTION,
        selected=None,
        assessments=(),
    )

    assert "No candidate satisfied" in rationale.summary
    assert "context=context-1" in rationale.factors