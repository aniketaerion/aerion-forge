"""EngineeringRequest builder for M5.9 Package 1."""

from __future__ import annotations

from pathlib import Path

from forge.general_engineering.identifiers import (
    engineering_request_identifier,
)
from forge.general_engineering.models import EngineeringRequest
from forge.general_engineering.normalization import (
    normalize_optional_items,
    normalize_repository_path,
    normalize_text,
)


def build_engineering_request(
    *,
    objective: str,
    repository_root: str | Path,
    constraints: tuple[str, ...] = (),
    acceptance_criteria: tuple[str, ...] = (),
    explicit_target_paths: tuple[str, ...] = (),
    forbidden_paths: tuple[str, ...] = (),
    allow_code_changes: bool = False,
    max_repair_attempts: int = 3,
) -> EngineeringRequest:
    """Create a normalized deterministic EngineeringRequest."""
    root = Path(repository_root).resolve()
    normalized_objective = normalize_text(objective)
    normalized_constraints = normalize_optional_items(constraints)
    normalized_acceptance = normalize_optional_items(acceptance_criteria)
    normalized_targets = tuple(
        normalize_repository_path(path) for path in explicit_target_paths
    )
    normalized_forbidden = tuple(
        normalize_repository_path(path) for path in forbidden_paths
    )

    payload = {
        "objective": normalized_objective,
        "repository_root": root.as_posix(),
        "constraints": normalized_constraints,
        "acceptance_criteria": normalized_acceptance,
        "explicit_target_paths": normalized_targets,
        "forbidden_paths": normalized_forbidden,
        "allow_code_changes": allow_code_changes,
        "max_repair_attempts": max_repair_attempts,
    }

    return EngineeringRequest(
        request_id=engineering_request_identifier(payload),
        objective=normalized_objective,
        repository_root=str(root),
        constraints=normalized_constraints,
        acceptance_criteria=normalized_acceptance,
        explicit_target_paths=normalized_targets,
        forbidden_paths=normalized_forbidden,
        allow_code_changes=allow_code_changes,
        max_repair_attempts=max_repair_attempts,
    )