"""Default-safe policies for autonomous memory."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_memory.errors import MemoryPolicyError


class MemoryLimitPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    maximum_observation_characters: int = Field(
        default=20000,
        ge=100,
        le=500000,
    )
    maximum_tags: int = Field(default=20, ge=0, le=100)
    maximum_evidence_references: int = Field(
        default=50,
        ge=0,
        le=500,
    )
    maximum_query_results: int = Field(
        default=20,
        ge=1,
        le=200,
    )


class MemoryConfidencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    minimum_fact_confidence: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
    )
    minimum_lesson_confidence: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
    )
    minimum_query_confidence: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
    )


class MemorySafetyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    require_provenance: bool = True
    facts_require_evidence: bool = True
    reject_secrets: bool = True
    repository_scope_by_default: bool = True
    include_superseded_by_default: bool = False
    allow_cross_repository_retrieval: bool = False
    allow_repository_mutation: bool = False
    allow_tool_execution: bool = False
    allow_automatic_policy_update: bool = False
    current_repository_evidence_wins: bool = True

    @model_validator(mode="after")
    def validate_safety(self) -> MemorySafetyPolicy:
        violations: list[str] = []

        if not self.require_provenance:
            violations.append("provenance is mandatory")
        if not self.facts_require_evidence:
            violations.append("facts require evidence")
        if not self.reject_secrets:
            violations.append("secret rejection is mandatory")
        if not self.repository_scope_by_default:
            violations.append("repository scope is mandatory")
        if self.include_superseded_by_default:
            violations.append(
                "superseded memory must be hidden by default"
            )
        if self.allow_cross_repository_retrieval:
            violations.append(
                "cross-repository retrieval requires approval"
            )
        if self.allow_repository_mutation:
            violations.append(
                "M5.5 cannot mutate repositories"
            )
        if self.allow_tool_execution:
            violations.append("M5.5 cannot execute tools")
        if self.allow_automatic_policy_update:
            violations.append(
                "memory cannot update policy automatically"
            )
        if not self.current_repository_evidence_wins:
            violations.append(
                "current repository evidence must outrank memory"
            )

        if violations:
            raise MemoryPolicyError("; ".join(violations))

        return self


class AutonomousMemoryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    policy_version: str = "1.0"
    limits: MemoryLimitPolicy = Field(
        default_factory=MemoryLimitPolicy
    )
    confidence: MemoryConfidencePolicy = Field(
        default_factory=MemoryConfidencePolicy
    )
    safety: MemorySafetyPolicy = Field(
        default_factory=MemorySafetyPolicy
    )