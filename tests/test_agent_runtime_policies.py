from datetime import UTC, datetime
from pathlib import Path

import pytest

from forge.agent_runtime.errors import (
    AgentRuntimeApprovalError,
    AgentRuntimePolicyError,
)
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentRuntimePolicy,
    AgentRuntimeRequest,
    ApprovalKind,
)
from forge.agent_runtime.policies import (
    require_approval,
    validate_request,
    validate_self_modification,
)


def test_policy_rejects_code_changes_by_default() -> None:
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
        allow_code_changes=True,
    )

    with pytest.raises(AgentRuntimePolicyError):
        validate_request(request, AgentRuntimePolicy())


def test_policy_rejects_disallowed_capability() -> None:
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
            requested_capabilities=(
                AgentCapability.AUTONOMOUS_REPAIR,
            ),
        ),
    )
    policy = AgentRuntimePolicy(
        allowed_capabilities=(
            AgentCapability.MISSION_PLANNING,
        )
    )

    with pytest.raises(AgentRuntimePolicyError):
        validate_request(request, policy)


def test_required_approval_is_enforced() -> None:
    with pytest.raises(AgentRuntimeApprovalError):
        require_approval(
            (),
            ApprovalKind.EDIT,
            AgentRuntimePolicy(),
        )


def test_latest_valid_approval_is_returned() -> None:
    approval = AgentApproval(
        approval_id="approval-1",
        kind=ApprovalKind.PLAN,
        approved=True,
        approved_by="operator",
        reason="approved",
        approved_at=datetime.now(UTC),
    )

    selected = require_approval(
        (approval,),
        ApprovalKind.PLAN,
        AgentRuntimePolicy(),
    )

    assert selected == approval


def test_self_modification_is_blocked(tmp_path: Path) -> None:
    runtime = tmp_path / "forge" / "agent_runtime"
    runtime.mkdir(parents=True)

    with pytest.raises(AgentRuntimePolicyError):
        validate_self_modification(
            tmp_path,
            ("forge/agent_runtime/models.py",),
            AgentRuntimePolicy(),
        )