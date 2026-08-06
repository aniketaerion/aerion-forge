from datetime import timedelta

import pytest

from forge.autonomous_runtime.approvals import (
    approval_covers_scope,
    approval_is_active,
    assert_approval_valid,
)
from forge.autonomous_runtime.errors import MissionPolicyError
from forge.autonomous_runtime.models import ApprovalDecision, utc_now
from forge.autonomous_runtime.states import AuthorityLevel


def approval() -> ApprovalDecision:
    return ApprovalDecision(
        approval_id="approval-1",
        mission_id="mission-1",
        decision="approve",
        authority_granted=AuthorityLevel.A4_COMMIT,
        scope=("forge/autonomous_runtime",),
        approved_by="Aerion",
        expires_at=utc_now() + timedelta(minutes=5),
    )


def test_active_approval_covers_scope() -> None:
    item = approval()

    assert approval_is_active(item)
    assert approval_covers_scope(
        item,
        ("forge/autonomous_runtime",),
    )


def test_wrong_mission_is_rejected() -> None:
    with pytest.raises(MissionPolicyError):
        assert_approval_valid(
            approval(),
            mission_id="mission-2",
            required_authority=AuthorityLevel.A4_COMMIT,
            requested_scope=("forge/autonomous_runtime",),
        )