"""Policy enforcement for M3.7 Build Verification."""

from __future__ import annotations

from pathlib import Path

from forge.build_verification.errors import BuildVerificationPolicyError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    BuildVerificationRequest,
    FindingSeverity,
    VerificationFinding,
)


def validate_request(
    request: BuildVerificationRequest,
    policy: BuildVerificationPolicy,
) -> None:
    if len(request.steps) > policy.max_steps:
        raise BuildVerificationPolicyError(
            f"request exceeds maximum step count: {policy.max_steps}"
        )

    for step in request.steps:
        if step.tool not in policy.allowed_tools:
            raise BuildVerificationPolicyError(
                f"verification tool is not allowed: {step.tool.value}"
            )
        if step.timeout_seconds > policy.max_timeout_seconds:
            raise BuildVerificationPolicyError(f"step timeout exceeds policy: {step.step_id}")
        if step.allow_network and not policy.allow_network:
            raise BuildVerificationPolicyError(f"network access is not allowed: {step.step_id}")


def resolve_repository_root(repository_root: str | Path) -> Path:
    root = Path(repository_root).expanduser().resolve()
    if not root.is_dir():
        raise BuildVerificationPolicyError(f"repository root does not exist: {root}")
    if not (root / ".git").exists():
        raise BuildVerificationPolicyError(f"repository root is not a Git repository: {root}")
    return root


def validate_target_paths(
    repository_root: Path,
    target_paths: tuple[str, ...],
) -> tuple[str, ...]:
    normalized: list[str] = []
    for raw_path in target_paths:
        candidate = (repository_root / raw_path).resolve()
        try:
            relative = candidate.relative_to(repository_root)
        except ValueError as exc:
            raise BuildVerificationPolicyError(
                f"target path escapes repository: {raw_path}"
            ) from exc
        normalized.append(relative.as_posix())
    return tuple(sorted(set(normalized)))


def blocking_finding_ids(
    findings: tuple[VerificationFinding, ...],
    policy: BuildVerificationPolicy,
) -> tuple[str, ...]:
    blocking: list[str] = []
    for finding in findings:
        if (
            finding.severity is FindingSeverity.CRITICAL and policy.reject_on_critical_findings
        ) or (finding.severity is FindingSeverity.HIGH and policy.reject_on_high_findings):
            blocking.append(finding.finding_id)
    return tuple(sorted(blocking))
