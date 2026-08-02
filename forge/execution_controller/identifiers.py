"""Deterministic Execution Controller identifiers."""

import hashlib
import json
from collections.abc import Mapping, Sequence

from forge.execution_controller.models import (
    ApprovalRecord,
    ExecutionEvidence,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionSession,
    ExecutionTransition,
)


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(
    namespace: str,
    payload: object,
    *,
    length: int = 20,
) -> str:
    value = (f"{namespace}:" + _canonical_json(payload)).encode("utf-8")

    return hashlib.sha256(value).hexdigest()[:length]


def execution_request_id(
    mission_id: str,
    task_ids: Sequence[str],
    requested_operations: Sequence[str],
    dry_run: bool,
    source_fingerprints: Mapping[str, str],
) -> str:
    payload = {
        "mission_id": mission_id.strip(),
        "task_ids": sorted(set(task_ids)),
        "requested_operations": sorted(set(requested_operations)),
        "dry_run": dry_run,
        "source_fingerprints": {
            key: source_fingerprints[key] for key in sorted(source_fingerprints)
        },
    }

    return "execution-request-" + _digest(
        "execution-request",
        payload,
    )


def execution_request_fingerprint(
    request: ExecutionRequest,
) -> str:
    payload = request.model_dump(
        mode="json",
        exclude={"request_fingerprint"},
    )
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def approval_id(
    request_fingerprint: str,
    approver_id: str,
    approved_operations: Sequence[str],
    evidence_reference: str,
) -> str:
    payload = {
        "request_fingerprint": request_fingerprint.strip(),
        "approver_id": approver_id.strip(),
        "approved_operations": sorted(set(approved_operations)),
        "evidence_reference": evidence_reference.strip(),
    }

    return "execution-approval-" + _digest(
        "execution-approval",
        payload,
    )


def transition_id(
    session_id: str,
    transition: ExecutionTransition,
    ordinal: int,
) -> str:
    payload = {
        "session_id": session_id.strip(),
        "ordinal": ordinal,
        "previous_state": transition.previous_state.value,
        "event": transition.event.value,
        "next_state": transition.next_state.value,
        "reason": transition.reason,
        "evidence_ids": list(transition.evidence_ids),
    }

    return "execution-transition-" + _digest(
        "execution-transition",
        payload,
    )


def operation_id(
    request_id: str,
    task_id: str,
    tool_id: str,
    operation_type: str,
    arguments_fingerprint: str,
) -> str:
    payload = {
        "request_id": request_id.strip(),
        "task_id": task_id.strip(),
        "tool_id": tool_id.strip(),
        "operation_type": operation_type.strip(),
        "arguments_fingerprint": (arguments_fingerprint.strip()),
    }

    return "execution-operation-" + _digest(
        "execution-operation",
        payload,
    )


def evidence_id(
    session_id: str,
    evidence: ExecutionEvidence,
) -> str:
    payload = {
        "session_id": session_id.strip(),
        "evidence_type": evidence.evidence_type.value,
        "source": evidence.source,
        "fingerprint": evidence.fingerprint,
        "reference": evidence.reference,
        "metadata": dict(evidence.metadata),
    }

    return "execution-evidence-" + _digest(
        "execution-evidence",
        payload,
    )


def session_id(
    request: ExecutionRequest,
    approval: ApprovalRecord | None,
) -> str:
    payload = {
        "request_id": request.request_id,
        "request_fingerprint": (request.request_fingerprint),
        "approval_id": (approval.approval_id if approval is not None else None),
    }

    return "execution-session-" + _digest(
        "execution-session",
        payload,
    )


def session_fingerprint(
    session: ExecutionSession,
) -> str:
    payload = session.model_dump(
        mode="json",
        exclude={"session_fingerprint"},
    )

    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def operation_fingerprint(
    operation: ExecutionOperation,
) -> str:
    return hashlib.sha256(
        _canonical_json(operation.model_dump(mode="json")).encode("utf-8")
    ).hexdigest()
