"""Impact identifier and policy tests."""

import pytest

from forge.impact.errors import ImpactValidationError
from forge.impact.identifiers import (
    build_assessment_id,
    build_generation_id,
    canonical_hash,
    validate_assessment_id,
    validate_fingerprint,
    validate_generation_id,
)
from forge.impact.models import (
    DecisionStatus,
    ImpactSeverity,
)
from forge.impact.policies import (
    MILESTONE_EXCLUSIONS,
    can_transition,
    highest_severity,
    is_terminal,
    validate_transition,
)


def test_canonical_hash_is_deterministic() -> None:
    assert canonical_hash({"b": 2, "a": 1}) == canonical_hash({"a": 1, "b": 2})


def test_assessment_id_is_deterministic() -> None:
    first = build_assessment_id(
        mission_id="mission-1",
        task_set_fingerprint="a" * 64,
        title="Review Procurement Impact",
        sequence=1,
    )
    second = build_assessment_id(
        mission_id="mission-1",
        task_set_fingerprint="a" * 64,
        title="Review Procurement Impact",
        sequence=1,
    )

    assert first == second
    assert validate_assessment_id(first)


def test_assessment_id_changes_for_identity_fields() -> None:
    first = build_assessment_id(
        mission_id="mission-1",
        task_set_fingerprint="a" * 64,
        title="Review Procurement Impact",
        sequence=1,
    )
    second = build_assessment_id(
        mission_id="mission-1",
        task_set_fingerprint="a" * 64,
        title="Review Inventory Impact",
        sequence=1,
    )

    assert first != second


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mission_id", ""),
        ("task_set_fingerprint", " "),
        ("title", ""),
    ],
)
def test_blank_identity_inputs_are_rejected(
    field: str,
    value: str,
) -> None:
    mission_id = "mission-1"
    task_set_fingerprint = "a" * 64
    title = "Assessment"

    if field == "mission_id":
        mission_id = value
    elif field == "task_set_fingerprint":
        task_set_fingerprint = value
    elif field == "title":
        title = value
    else:
        raise AssertionError(f"Unexpected test field: {field}")

    with pytest.raises(ImpactValidationError):
        build_assessment_id(
            mission_id=mission_id,
            task_set_fingerprint=task_set_fingerprint,
            title=title,
            sequence=1,
        )


def test_negative_sequence_is_rejected() -> None:
    with pytest.raises(ImpactValidationError):
        build_assessment_id(
            mission_id="mission-1",
            task_set_fingerprint="a" * 64,
            title="Assessment",
            sequence=-1,
        )


def test_generation_id_is_deterministic() -> None:
    first = build_generation_id(
        assessment_id="impact-" + "a" * 20,
        assessment_fingerprint="b" * 64,
    )
    second = build_generation_id(
        assessment_id="impact-" + "a" * 20,
        assessment_fingerprint="b" * 64,
    )

    assert first == second
    assert validate_generation_id(first)


def test_fingerprint_validation() -> None:
    assert validate_fingerprint("a" * 64)
    assert not validate_fingerprint("not-a-fingerprint")


def test_valid_transitions_are_allowed() -> None:
    assert can_transition(
        DecisionStatus.DRAFT,
        DecisionStatus.READY,
    )
    assert can_transition(
        DecisionStatus.BLOCKED,
        DecisionStatus.DRAFT,
    )


def test_terminal_status_rejects_transition() -> None:
    assert is_terminal(DecisionStatus.SUPERSEDED)
    assert not can_transition(
        DecisionStatus.SUPERSEDED,
        DecisionStatus.READY,
    )

    with pytest.raises(ImpactValidationError):
        validate_transition(
            DecisionStatus.SUPERSEDED,
            DecisionStatus.READY,
        )


def test_highest_severity_uses_controlled_order() -> None:
    assert (
        highest_severity(
            (
                ImpactSeverity.LOW,
                ImpactSeverity.CRITICAL,
                ImpactSeverity.HIGH,
            )
        )
        is ImpactSeverity.CRITICAL
    )
    assert highest_severity(()) is ImpactSeverity.UNKNOWN


def test_milestone_exclusions_preserve_boundary() -> None:
    assert "task execution" in MILESTONE_EXCLUSIONS
    assert "source-code modification" in MILESTONE_EXCLUSIONS
    assert "deployment" in MILESTONE_EXCLUSIONS
    assert "approval granting" in MILESTONE_EXCLUSIONS
