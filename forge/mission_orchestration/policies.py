"""Safety policy for M3.6 Mission Orchestration."""

from __future__ import annotations

from pathlib import Path, PurePosixPath

from pydantic import Field

from forge.mission_orchestration.errors import MissionPolicyViolationError
from forge.mission_orchestration.models import FrozenModel, StageType


class MissionOrchestrationPolicy(FrozenModel):
    max_stage_attempts: int = Field(default=3, ge=1, le=10)
    max_total_stage_runs: int = Field(default=50, ge=1, le=500)
    max_requested_paths: int = Field(default=25, ge=1, le=500)
    require_approval_for_apply: bool = True
    require_approval_for_high_risk: bool = True
    require_repository_fingerprint: bool = True
    checkpoint_after_each_stage: bool = True
    stop_on_repository_state_change: bool = True
    allow_resume: bool = True
    allow_cancellation: bool = True
    allow_git_mutation: bool = False
    allow_dependency_installation: bool = False
    allow_arbitrary_shell: bool = False
    protected_paths: tuple[str, ...] = (
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "reports",
        "audit",
        "memory",
    )
    required_stages: tuple[StageType, ...] = (
        StageType.MISSION_VALIDATION,
        StageType.EXECUTION_REQUEST,
        StageType.SAFE_CHANGE_PLAN,
        StageType.IMPACT_ASSESSMENT,
        StageType.APPROVAL_GATE,
        StageType.SAFE_EDIT_DRY_RUN,
        StageType.SAFE_EDIT_APPLY,
        StageType.VALIDATION,
        StageType.FINAL_VALIDATION,
        StageType.MISSION_REPORTING,
    )

    def validate_paths(self, paths: tuple[str, ...]) -> tuple[str, ...]:
        if len(paths) > self.max_requested_paths:
            raise MissionPolicyViolationError(
                "mission exceeds maximum requested paths"
            )
        normalized: list[str] = []
        for raw_path in paths:
            path = PurePosixPath(raw_path.replace("\\", "/").strip())
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise MissionPolicyViolationError(
                    f"invalid mission path: {raw_path}"
                )
            if path.parts[0] in self.protected_paths:
                raise MissionPolicyViolationError(
                    f"protected mission path: {raw_path}"
                )
            normalized.append(path.as_posix())
        return tuple(normalized)

    def validate_stage_attempts(self, attempts: int) -> None:
        if attempts > self.max_stage_attempts:
            raise MissionPolicyViolationError(
                "stage attempt count exceeds policy limit"
            )

    @staticmethod
    def resolve_repository(repository_root: Path) -> Path:
        root = repository_root.expanduser().resolve()
        if not root.is_dir():
            raise MissionPolicyViolationError(
                f"repository root does not exist: {root}"
            )
        return root