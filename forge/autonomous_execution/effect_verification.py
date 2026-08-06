"""Verification of actual repository effects against approved scope."""

from __future__ import annotations

from pathlib import PurePosixPath

from forge.autonomous_execution.errors import ToolContractError


def _normalized(path: str) -> str:
    return PurePosixPath(path.replace("\\", "/")).as_posix().lstrip("./")


def _is_within(
    path: str,
    scope: str,
) -> bool:
    normalized_path = _normalized(path)
    normalized_scope = _normalized(scope).rstrip("/")

    return (
        normalized_path == normalized_scope
        or normalized_path.startswith(normalized_scope + "/")
    )


def verify_affected_files(
    affected_files: tuple[str, ...],
    approved_scope: tuple[str, ...],
) -> None:
    """Reject repository effects outside approved scope."""
    if not affected_files:
        return

    if not approved_scope:
        raise ToolContractError(
            "Affected files exist but approved scope is empty."
        )

    violations = tuple(
        path
        for path in affected_files
        if not any(
            _is_within(path, scope)
            for scope in approved_scope
        )
    )

    if violations:
        raise ToolContractError(
            "Tool affected files outside approved scope: "
            + ", ".join(sorted(violations))
        )