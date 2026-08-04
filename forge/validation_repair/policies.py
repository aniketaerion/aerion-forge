"""Safety policy for validation and repair."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from forge.validation_repair.errors import (
    InvalidValidationCommandError,
    RepairApprovalRequiredError,
)
from forge.validation_repair.models import FrozenModel, ValidationCommand, ValidationTool


class ValidationRepairPolicy(FrozenModel):
    """Immutable policy for bounded validation and repair."""

    max_repair_attempts: int = Field(default=3, ge=1, le=10)
    default_timeout_seconds: int = Field(default=300, gt=0)
    allowed_tools: tuple[ValidationTool, ...] = (
        ValidationTool.RUFF,
        ValidationTool.MYPY,
        ValidationTool.PYTEST,
    )
    require_explicit_approval: bool = True
    dry_run_default: bool = True
    rollback_failed_repairs: bool = True
    stop_on_repository_state_change: bool = True
    allow_shell: bool = False

    def validate_command(self, command: ValidationCommand) -> None:
        """Reject unsupported tools and unsafe argument forms."""
        if command.tool not in self.allowed_tools:
            raise InvalidValidationCommandError(
                f"validation tool is not permitted: {command.tool}"
            )

        forbidden_tokens = {";", "&&", "||", "|", ">", "<"}
        if any(token in argument for argument in command.arguments for token in forbidden_tokens):
            raise InvalidValidationCommandError(
                "shell metacharacters are not permitted in validation arguments"
            )

    def validate_apply_mode(self, *, dry_run: bool, approved: bool) -> None:
        """Require explicit approval for applied repairs."""
        if not dry_run and self.require_explicit_approval and not approved:
            raise RepairApprovalRequiredError(
                "repair application requires explicit approval"
            )

    @staticmethod
    def resolve_repository(repository_root: Path) -> Path:
        """Resolve and validate the repository root."""
        root = repository_root.expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"repository root does not exist: {root}")
        return root