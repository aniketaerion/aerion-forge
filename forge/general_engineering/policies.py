"""Policies for the M5.9 General Engineering Agent."""

from __future__ import annotations

from pathlib import PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.general_engineering.errors import EngineeringPolicyError


class EngineeringLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    max_target_files: int = Field(default=20, ge=1, le=200)
    max_edit_operations: int = Field(default=100, ge=1, le=1000)
    max_repair_attempts: int = Field(default=3, ge=0, le=3)
    max_generated_content_bytes: int = Field(
        default=2_000_000,
        ge=1,
        le=20_000_000,
    )


class EngineeringSafetyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    require_repository_grounding: bool = True
    require_plan_approval: bool = True
    require_edit_approval: bool = True
    require_release_approval: bool = True
    require_source_fingerprints_for_destructive_edits: bool = True
    allow_direct_provider_file_writes: bool = False
    allow_arbitrary_shell_execution: bool = False
    allow_scope_expansion_without_reapproval: bool = False
    allow_self_modification: bool = False


class EngineeringScopePolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    forbidden_paths: tuple[str, ...] = (
        ".git",
        ".venv",
        "venv",
        "__pycache__",
    )

    @model_validator(mode="after")
    def validate_forbidden_paths(self) -> EngineeringScopePolicy:
        normalized = tuple(_normalize_relative_path(path) for path in self.forbidden_paths)
        if len(normalized) != len(set(normalized)):
            raise EngineeringPolicyError("Forbidden paths must be unique.")
        return self


class GeneralEngineeringPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    limits: EngineeringLimits = Field(default_factory=EngineeringLimits)
    safety: EngineeringSafetyPolicy = Field(
        default_factory=EngineeringSafetyPolicy
    )
    scope: EngineeringScopePolicy = Field(
        default_factory=EngineeringScopePolicy
    )


def _normalize_relative_path(path: str) -> str:
    stripped = path.strip().replace("\\", "/")
    if not stripped:
        raise EngineeringPolicyError("Policy path cannot be empty.")
    pure = PurePosixPath(stripped)
    if pure.is_absolute() or ".." in pure.parts:
        raise EngineeringPolicyError(
            f"Policy path must remain repository-relative: {path!r}"
        )
    return pure.as_posix()


def is_forbidden_path(
    path: str,
    policy: EngineeringScopePolicy,
) -> bool:
    normalized = _normalize_relative_path(path)
    target = PurePosixPath(normalized)

    for forbidden in policy.forbidden_paths:
        base = PurePosixPath(_normalize_relative_path(forbidden))
        if target == base or base in target.parents:
            return True
    return False