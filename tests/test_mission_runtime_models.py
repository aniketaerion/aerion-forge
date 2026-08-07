import pytest

from forge.mission_runtime.errors import MissionContractError
from forge.mission_runtime.models import (
    MissionApproval,
    MissionEvidence,
    MissionRequest,
    MissionSession,
)
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionApprovalKind,
    MissionEvidenceKind,
    MissionState,
)


def test_request_rejects_empty_statement() -> None:
    with pytest.raises(MissionContractError):
        MissionRequest(
            request_id="request-1",
            workspace_id="workspace-1",
            repository_root="repository",
            statement="",
            requested_by="Aerion",
        )


def test_decided_approval_requires_approver() -> None:
    with pytest.raises(MissionContractError):
        MissionApproval(
            approval_id="approval-1",
            session_id="session-1",
            kind=MissionApprovalKind.PLAN,
            decision=MissionApprovalDecision.APPROVED,
            rationale="Plan approved.",
        )


def test_evidence_requires_references() -> None:
    with pytest.raises(MissionContractError):
        MissionEvidence(
            evidence_id="evidence-1",
            session_id="session-1",
            kind=MissionEvidenceKind.PLAN,
            references=(),
            summary="Plan generated.",
        )


def test_completed_session_requires_verification() -> None:
    with pytest.raises(MissionContractError):
        MissionSession(
            session_id="session-1",
            request_id="request-1",
            workspace_id="workspace-1",
            repository_root="repository",
            repository_fingerprint="fingerprint",
            state=MissionState.COMPLETED,
        )