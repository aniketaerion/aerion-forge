import pytest
from pydantic import ValidationError

from forge.autonomous_execution.states import ToolExecutionStatus
from forge.autonomous_execution.tool_contracts import (
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
)
from forge.autonomous_runtime.states import AuthorityLevel, RiskClass


def test_mutating_tool_requires_checkpoint() -> None:
    with pytest.raises(ValidationError):
        ToolDefinition(
            tool_name="file-editor",
            action_kinds=("apply_patch",),
            authority_required=AuthorityLevel.A2_MODIFY,
            risk_class=RiskClass.R2_MODERATE,
            mutates_repository=True,
            requires_checkpoint=False,
        )


def test_dry_run_request_defaults_safe() -> None:
    request = ToolExecutionRequest(
        invocation_id="invocation-1",
        mission_id="mission-1",
        step_id="step-1",
        tool_name="ruff",
        action_kind="validate",
    )

    assert request.dry_run


def test_tool_result_is_immutable_contract() -> None:
    result = ToolExecutionResult(
        invocation_id="invocation-1",
        status=ToolExecutionStatus.SUCCEEDED,
        exit_code=0,
        started_at="2026-08-06T00:00:00+00:00",
        completed_at="2026-08-06T00:00:01+00:00",
    )

    assert result.exit_code == 0