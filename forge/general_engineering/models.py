"""Immutable contracts for the M5.9 General Engineering Agent."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
    EngineeringTerminalStatus,
    EvidenceType,
    RepairDisposition,
    ValidationStatus,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _validate_relative_path(path: str, field_name: str) -> str:
    stripped = path.strip().replace("\\", "/")
    if not stripped:
        raise EngineeringContractError(f"{field_name} cannot be empty.")

    pure = PurePosixPath(stripped)
    if pure.is_absolute() or ".." in pure.parts:
        raise EngineeringContractError(
            f"{field_name} must be repository-relative: {path!r}"
        )
    return pure.as_posix()


class EngineeringRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    objective: str
    repository_root: str
    constraints: tuple[str, ...] = ()
    acceptance_criteria: tuple[str, ...] = ()
    explicit_target_paths: tuple[str, ...] = ()
    forbidden_paths: tuple[str, ...] = ()
    allow_code_changes: bool = False
    max_repair_attempts: int = Field(default=3, ge=0, le=3)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_request(self) -> EngineeringRequest:
        if not self.request_id.strip():
            raise EngineeringContractError("Request ID cannot be empty.")
        if not self.objective.strip():
            raise EngineeringContractError("Objective cannot be empty.")
        if not self.repository_root.strip():
            raise EngineeringContractError("Repository root cannot be empty.")

        root = Path(self.repository_root)
        if not root.is_absolute():
            raise EngineeringContractError(
                "Repository root must be an absolute path."
            )

        for path in self.explicit_target_paths:
            _validate_relative_path(path, "Explicit target path")
        for path in self.forbidden_paths:
            _validate_relative_path(path, "Forbidden path")
        return self


class RepositoryEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    path: str
    evidence_type: EvidenceType
    rationale: str
    relevance: float = Field(ge=0.0, le=1.0)
    symbol: str | None = None
    fingerprint: str | None = None
    provenance: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_evidence(self) -> RepositoryEvidence:
        _validate_relative_path(self.path, "Evidence path")
        if not self.rationale.strip():
            raise EngineeringContractError(
                "Repository evidence requires rationale."
            )
        return self


class RelevantSymbol(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    kind: str
    path: str
    evidence_ids: tuple[str, ...]
    rationale: str

    @model_validator(mode="after")
    def validate_symbol(self) -> RelevantSymbol:
        _validate_relative_path(self.path, "Relevant symbol path")
        if not self.name.strip() or not self.kind.strip():
            raise EngineeringContractError(
                "Relevant symbol requires name and kind."
            )
        if not self.evidence_ids:
            raise EngineeringContractError(
                "Relevant symbol requires repository evidence."
            )
        if not self.rationale.strip():
            raise EngineeringContractError(
                "Relevant symbol requires rationale."
            )
        return self


class RelevantFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    evidence_ids: tuple[str, ...]
    rationale: str
    symbols: tuple[RelevantSymbol, ...] = ()

    @model_validator(mode="after")
    def validate_file(self) -> RelevantFile:
        _validate_relative_path(self.path, "Relevant file path")
        if not self.evidence_ids:
            raise EngineeringContractError(
                "Relevant file requires repository evidence."
            )
        if not self.rationale.strip():
            raise EngineeringContractError(
                "Relevant file requires rationale."
            )
        return self


class EngineeringContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    relevant_files: tuple[RelevantFile, ...]
    evidence: tuple[RepositoryEvidence, ...]

    @model_validator(mode="after")
    def validate_context(self) -> EngineeringContext:
        if not self.relevant_files:
            raise EngineeringContractError(
                "Engineering context requires relevant files."
            )
        if not self.evidence:
            raise EngineeringContractError(
                "Engineering context requires repository evidence."
            )

        evidence_ids = {item.evidence_id for item in self.evidence}
        for file in self.relevant_files:
            missing = set(file.evidence_ids) - evidence_ids
            if missing:
                raise EngineeringContractError(
                    "Relevant file references unknown evidence: "
                    + ", ".join(sorted(missing))
                )
        return self


class ChangeRequirement(BaseModel):
    model_config = ConfigDict(frozen=True)

    requirement_id: str
    description: str
    acceptance_criteria: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_requirement(self) -> ChangeRequirement:
        if not self.description.strip():
            raise EngineeringContractError(
                "Change requirement description cannot be empty."
            )
        return self


class ChangeSpecification(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    requirements: tuple[ChangeRequirement, ...]
    constraints: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_specification(self) -> ChangeSpecification:
        if not self.requirements:
            raise EngineeringContractError(
                "Change specification requires at least one requirement."
            )
        return self


class FileChangePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    rationale: str
    evidence_ids: tuple[str, ...]
    relevant_symbols: tuple[str, ...] = ()
    intended_operations: tuple[EditOperationType, ...]
    dependencies: tuple[str, ...] = ()
    expected_effect: str
    risk: EngineeringRisk = EngineeringRisk.MEDIUM

    @model_validator(mode="after")
    def validate_file_plan(self) -> FileChangePlan:
        _validate_relative_path(self.path, "File change path")
        if not self.rationale.strip():
            raise EngineeringContractError(
                "File change plan requires rationale."
            )
        if not self.evidence_ids:
            raise EngineeringContractError(
                "File change plan requires repository evidence."
            )
        if not self.intended_operations:
            raise EngineeringContractError(
                "File change plan requires intended operations."
            )
        if not self.expected_effect.strip():
            raise EngineeringContractError(
                "File change plan requires expected effect."
            )
        return self


class ValidationPlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    validation_plan_id: str
    commands: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_plan(self) -> ValidationPlan:
        if not self.commands and not self.capabilities:
            raise EngineeringContractError(
                "Validation plan requires commands or capabilities."
            )
        return self


class ChangePlan(BaseModel):
    model_config = ConfigDict(frozen=True)

    plan_id: str
    request_id: str
    objective: str
    requirements: tuple[ChangeRequirement, ...]
    file_changes: tuple[FileChangePlan, ...]
    validation_plan: ValidationPlan
    expected_effect: str
    aggregate_risk: EngineeringRisk
    evidence_ids: tuple[str, ...]
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_change_plan(self) -> ChangePlan:
        if not self.objective.strip():
            raise EngineeringContractError(
                "Change plan objective cannot be empty."
            )
        if not self.requirements:
            raise EngineeringContractError(
                "Change plan requires requirements."
            )
        if not self.file_changes:
            raise EngineeringContractError(
                "Change plan requires at least one file change."
            )
        if not self.evidence_ids:
            raise EngineeringContractError(
                "Change plan requires repository evidence."
            )
        if not self.expected_effect.strip():
            raise EngineeringContractError(
                "Change plan requires expected effect."
            )
        return self


class EditOperation(BaseModel):
    model_config = ConfigDict(frozen=True)

    operation_id: str
    operation_type: EditOperationType
    target_path: str
    rationale: str
    originating_requirement_id: str
    target_symbol: str | None = None
    source_fingerprint: str | None = None
    proposed_content: str | None = None
    rename_target_path: str | None = None
    evidence_ids: tuple[str, ...] = ()
    order: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_operation(self) -> EditOperation:
        _validate_relative_path(self.target_path, "Edit target path")

        if self.rename_target_path is not None:
            _validate_relative_path(
                self.rename_target_path,
                "Rename target path",
            )

        if not self.rationale.strip():
            raise EngineeringContractError(
                "Edit operation requires rationale."
            )

        if not self.originating_requirement_id.strip():
            raise EngineeringContractError(
                "Edit operation requires an originating requirement."
            )

        if self.operation_type is EditOperationType.RENAME:
            if not self.rename_target_path:
                raise EngineeringContractError(
                    "RENAME operation requires rename_target_path."
                )
        elif self.rename_target_path is not None:
            raise EngineeringContractError(
                "rename_target_path is valid only for RENAME operations."
            )

        if self.operation_type in {
            EditOperationType.CREATE_FILE,
            EditOperationType.INSERT,
            EditOperationType.REPLACE,
        } and self.proposed_content is None:
            raise EngineeringContractError(
                f"{self.operation_type.value} requires proposed_content."
            )

        if self.operation_type in {
            EditOperationType.REPLACE,
            EditOperationType.DELETE,
            EditOperationType.RENAME,
        } and not self.source_fingerprint:
            raise EngineeringContractError(
                f"{self.operation_type.value} requires source_fingerprint."
            )

        return self


class GeneratedChangeSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    change_set_id: str
    plan_id: str
    operations: tuple[EditOperation, ...]
    evidence_ids: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_change_set(self) -> GeneratedChangeSet:
        if not self.operations:
            raise EngineeringContractError(
                "Generated change set requires operations."
            )

        ordered = tuple(sorted(self.operations, key=lambda item: item.order))
        if ordered != self.operations:
            raise EngineeringContractError(
                "Generated change set operations must already be ordered."
            )

        operation_ids = [item.operation_id for item in self.operations]
        if len(operation_ids) != len(set(operation_ids)):
            raise EngineeringContractError(
                "Generated change set operation IDs must be unique."
            )
        return self


class ValidationOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    outcome_id: str
    validation_plan_id: str
    status: ValidationStatus
    summary: str
    commands_run: tuple[str, ...] = ()
    failures: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_outcome(self) -> ValidationOutcome:
        if not self.summary.strip():
            raise EngineeringContractError(
                "Validation outcome requires summary."
            )
        if (
            self.status is ValidationStatus.FAILED
            and not self.failures
        ):
            raise EngineeringContractError(
                "Failed validation requires failure evidence."
            )
        return self


class RepairProposal(BaseModel):
    model_config = ConfigDict(frozen=True)

    repair_id: str
    request_id: str
    attempt_number: int = Field(ge=1, le=3)
    diagnosis: str
    target_paths: tuple[str, ...]
    validation_outcome_id: str
    proposed_change_set_id: str | None = None
    disposition: RepairDisposition = RepairDisposition.PROPOSED
    risk: EngineeringRisk = EngineeringRisk.MEDIUM

    @model_validator(mode="after")
    def validate_repair(self) -> RepairProposal:
        if not self.diagnosis.strip():
            raise EngineeringContractError(
                "Repair proposal requires diagnosis."
            )
        if not self.target_paths:
            raise EngineeringContractError(
                "Repair proposal requires bounded target paths."
            )
        for path in self.target_paths:
            _validate_relative_path(path, "Repair target path")
        return self


class EngineeringEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    request_id: str
    repository_evidence_ids: tuple[str, ...]
    plan_id: str | None = None
    change_set_id: str | None = None
    validation_outcome_ids: tuple[str, ...] = ()
    repair_ids: tuple[str, ...] = ()
    approval_ids: tuple[str, ...] = ()
    terminal_status: EngineeringTerminalStatus
    summary: str
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_engineering_evidence(self) -> EngineeringEvidence:
        if not self.repository_evidence_ids:
            raise EngineeringContractError(
                "Engineering evidence requires repository evidence."
            )
        if not self.summary.strip():
            raise EngineeringContractError(
                "Engineering evidence summary cannot be empty."
            )
        return self