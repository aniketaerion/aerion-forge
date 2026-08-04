"""Safety policy for M3.5 Autonomous Repair."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from pydantic import Field

from forge.autonomous_repair.errors import (
    RepairApprovalRequiredError,
    RepairPolicyViolationError,
)
from forge.autonomous_repair.models import FrozenModel, RepairProviderType


class AutonomousRepairPolicy(FrozenModel):
    """Immutable bounded repair policy."""

    max_attempts: int = Field(default=3, ge=1, le=10)
    max_files_per_attempt: int = Field(default=5, ge=1, le=100)
    max_changed_bytes: int = Field(default=250_000, ge=1)
    allowed_providers: tuple[RepairProviderType, ...] = (
        RepairProviderType.EXACT_PATCH,
        RepairProviderType.RUFF_FIX,
    )
    protected_paths: tuple[str, ...] = (
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "reports",
        "audit",
        "memory",
    )
    dry_run_default: bool = True
    require_explicit_approval: bool = True
    require_source_fingerprints: bool = True
    rollback_on_failed_validation: bool = True
    stop_on_repository_state_change: bool = True
    allow_shell: bool = False
    allow_git_mutation: bool = False
    allow_dependency_changes: bool = False

    def validate_provider(self, provider: RepairProviderType) -> None:
        """Reject providers not permitted by policy."""
        if provider not in self.allowed_providers:
            raise RepairPolicyViolationError(
                f"repair provider is not permitted: {provider}"
            )

    def validate_apply_mode(self, *, dry_run: bool, approved: bool) -> None:
        """Require explicit approval for mutation."""
        if not dry_run and self.require_explicit_approval and not approved:
            raise RepairApprovalRequiredError(
                "repair application requires explicit approval"
            )

    def validate_paths(self, paths: tuple[str, ...]) -> tuple[str, ...]:
        """Normalize and reject protected or unsafe paths."""
        if len(paths) > self.max_files_per_attempt:
            raise RepairPolicyViolationError(
                "repair exceeds maximum files per attempt"
            )

        normalized: list[str] = []
        for raw_path in paths:
            path = PurePosixPath(raw_path.replace("\\", "/").strip())
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise RepairPolicyViolationError(f"invalid repair path: {raw_path}")
            if path.parts[0] in self.protected_paths:
                raise RepairPolicyViolationError(f"protected repair path: {raw_path}")
            normalized.append(path.as_posix())
        return tuple(normalized)

    @staticmethod
    def resolve_repository(repository_root: Path) -> Path:
        """Resolve and validate repository root."""
        root = repository_root.expanduser().resolve()
        if not root.is_dir():
            raise RepairPolicyViolationError(
                f"repository root does not exist: {root}"
            )
        return root