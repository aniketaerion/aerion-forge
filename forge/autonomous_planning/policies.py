"""Default-safe policies for autonomous planning."""

from pydantic import BaseModel, ConfigDict, Field


class PlanningLimits(BaseModel):
    model_config = ConfigDict(frozen=True)

    maximum_steps: int = Field(default=50, ge=1, le=500)
    maximum_dependencies: int = Field(default=200, ge=0, le=5000)
    maximum_target_paths: int = Field(default=100, ge=1, le=1000)
    maximum_constraints: int = Field(default=100, ge=0, le=1000)


class PlanningSafetyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    require_repository_scope: bool = True
    require_acceptance_criteria: bool = True
    reject_empty_objective: bool = True
    reject_path_escape: bool = True
    require_approval_for_high_risk: bool = True
    require_approval_for_release: bool = True
    require_validation_step: bool = True
    allow_destructive_steps: bool = False


class PlanningQualityPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    minimum_step_description_length: int = Field(default=10, ge=1, le=500)
    require_unique_step_names: bool = True
    require_dependency_acyclicity: bool = True
    require_deterministic_ordering: bool = True
    require_traceability: bool = True


class AutonomousPlanningPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)

    limits: PlanningLimits = Field(default_factory=PlanningLimits)
    safety: PlanningSafetyPolicy = Field(default_factory=PlanningSafetyPolicy)
    quality: PlanningQualityPolicy = Field(default_factory=PlanningQualityPolicy)