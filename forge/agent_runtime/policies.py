"""Policy enforcement for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from pathlib import Path

from forge.agent_runtime.errors import (
    AgentRuntimeApprovalError,
    AgentRuntimePolicyError,
)
from forge.agent_runtime.models import (
    AgentApproval,
    AgentRuntimePolicy,
    AgentRuntimeRequest,
    ApprovalKind,
)


def resolve_repository_root(
    repository_root: str | Path,
) -> Path:
    """Resolve and validate a Git repository root."""
    root = Path(repository_root).expanduser().resolve()

    if not root.is_dir():
        raise AgentRuntimePolicyError(
            f"repository root does not exist: {root}"
        )

    if not (root / ".git").exists():
        raise AgentRuntimePolicyError(
            f"repository root is not a Git repository: {root}"
        )

    return root


def validate_request(
    request: AgentRuntimeRequest,
    policy: AgentRuntimePolicy,
) -> None:
    """Validate a runtime request against safety policy."""
    if request.max_stages > policy.max_stages:
        raise AgentRuntimePolicyError(
            f"request exceeds maximum stage count: {policy.max_stages}"
        )

    if request.max_repair_attempts > policy.max_repair_attempts:
        raise AgentRuntimePolicyError(
            "request exceeds maximum repair attempts"
        )

    requested = set(request.objective.requested_capabilities)
    allowed = set(policy.allowed_capabilities)
    disallowed = requested - allowed

    if disallowed:
        names = ", ".join(sorted(item.value for item in disallowed))
        raise AgentRuntimePolicyError(
            f"requested capabilities are not allowed: {names}"
        )

    if request.allow_code_changes and not policy.allow_code_changes:
        raise AgentRuntimePolicyError(
            "code changes are disabled by runtime policy"
        )


def approval_required(
    kind: ApprovalKind,
    policy: AgentRuntimePolicy,
) -> bool:
    """Return whether policy requires the given approval kind."""
    mapping = {
        ApprovalKind.PLAN: policy.require_plan_approval,
        ApprovalKind.EDIT: policy.require_edit_approval,
        ApprovalKind.REPAIR: policy.require_repair_approval,
        ApprovalKind.RELEASE: policy.require_release_approval,
    }
    return mapping[kind]


def require_approval(
    approvals: tuple[AgentApproval, ...],
    kind: ApprovalKind,
    policy: AgentRuntimePolicy,
) -> AgentApproval | None:
    """Return a valid approval or fail closed."""
    if not approval_required(kind, policy):
        return None

    matching = [
        approval
        for approval in approvals
        if approval.kind is kind and approval.approved
    ]

    if not matching:
        raise AgentRuntimeApprovalError(
            f"missing required approval: {kind.value}"
        )

    return max(matching, key=lambda item: item.approved_at)


def validate_self_modification(
    repository_root: Path,
    target_paths: tuple[str, ...],
    policy: AgentRuntimePolicy,
) -> None:
    """Reject runtime self-modification unless explicitly enabled."""
    if policy.allow_self_modification:
        return

    runtime_root = (repository_root / "forge" / "agent_runtime").resolve()

    for relative_path in target_paths:
        candidate = (repository_root / relative_path).resolve()

        try:
            candidate.relative_to(runtime_root)
        except ValueError:
            continue

        raise AgentRuntimePolicyError(
            "self-modification of agent_runtime is disabled"
        )