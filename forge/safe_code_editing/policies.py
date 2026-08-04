"""Safety policy for bounded code editing."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from pydantic import Field

from forge.safe_code_editing.errors import (
    ApprovalRequiredError,
    InvalidEditPathError,
    RepositoryPathEscapeError,
)

from .models import FrozenModel


class SafeEditPolicy(FrozenModel):
    """Immutable editing policy."""

    max_file_bytes: int = Field(default=1_000_000, gt=0)
    allowed_encodings: tuple[str, ...] = ("utf-8", "utf-8-sig")
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
    reject_symlink_escape: bool = True

    def validate_apply_mode(self, *, dry_run: bool, approved: bool) -> None:
        """Reject unapproved apply requests."""
        if not dry_run and self.require_explicit_approval and not approved:
            raise ApprovalRequiredError("apply mode requires explicit approval")

    def validate_relative_path(self, relative_path: str) -> str:
        """Normalize and validate a repository-relative path."""
        normalized = relative_path.replace("\\", "/").strip()
        path = PurePosixPath(normalized)
        if not normalized or path.is_absolute() or ".." in path.parts:
            raise InvalidEditPathError(f"invalid relative path: {relative_path}")
        if path.parts and path.parts[0] in self.protected_paths:
            raise InvalidEditPathError(f"protected path: {relative_path}")
        return path.as_posix()

    def resolve_path(self, repository_root: Path, relative_path: str) -> Path:
        """Resolve a path and guarantee repository containment."""
        normalized = self.validate_relative_path(relative_path)
        root = repository_root.resolve()
        candidate = (root / normalized).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise RepositoryPathEscapeError(
                f"path resolves outside repository: {relative_path}"
            ) from exc
        if self.reject_symlink_escape and candidate.exists() and candidate.is_symlink():
            resolved = candidate.resolve()
            try:
                resolved.relative_to(root)
            except ValueError as exc:
                raise RepositoryPathEscapeError(
                    f"symlink resolves outside repository: {relative_path}"
                ) from exc
        return candidate