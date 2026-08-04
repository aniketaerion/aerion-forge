"""Immutable contracts for Safe Code Editing v1."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EditOperationType(StrEnum):
    """Supported bounded edit operations."""

    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"


def _validate_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute():
        raise ValueError("path must be relative")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("path may not contain empty, current, or parent traversal segments")
    return path.as_posix()


class FrozenModel(BaseModel):
    """Base class for immutable Forge contracts."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class EditOperation(FrozenModel):
    """One deterministic text edit."""

    operation_id: str
    operation_type: EditOperationType
    relative_path: str
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(ge=0)]
    expected_text: str = ""
    replacement_text: str = ""
    source_fingerprint: str

    @model_validator(mode="after")
    def validate_operation(self) -> EditOperation:
        object.__setattr__(self, "relative_path", _validate_relative_path(self.relative_path))
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset may not precede start_offset")
        if self.operation_type is EditOperationType.INSERT:
            if self.start_offset != self.end_offset:
                raise ValueError("INSERT requires equal start_offset and end_offset")
            if self.expected_text:
                raise ValueError("INSERT must not require expected_text")
        elif self.operation_type is EditOperationType.DELETE:
            if self.replacement_text:
                raise ValueError("DELETE requires empty replacement_text")
            if not self.expected_text:
                raise ValueError("DELETE requires expected_text")
        elif self.operation_type is EditOperationType.REPLACE:
            if not self.expected_text:
                raise ValueError("REPLACE requires expected_text")
        return self


class FileEditPlan(FrozenModel):
    """Ordered edits for one file."""

    relative_path: str
    source_fingerprint: str
    operations: tuple[EditOperation, ...]

    @model_validator(mode="after")
    def validate_plan(self) -> FileEditPlan:
        object.__setattr__(self, "relative_path", _validate_relative_path(self.relative_path))
        if not self.operations:
            raise ValueError("file edit plan requires at least one operation")
        if any(operation.relative_path != self.relative_path for operation in self.operations):
            raise ValueError("all operations must target the file edit plan path")
        operation_ids = [operation.operation_id for operation in self.operations]
        if len(operation_ids) != len(set(operation_ids)):
            raise ValueError("duplicate operation IDs are not allowed")
        return self


class SafeEditRequest(FrozenModel):
    """Approved or dry-run request derived from an M3.2 change plan."""

    request_id: str
    change_plan_id: str
    repository_root: str
    file_plans: tuple[FileEditPlan, ...]
    dry_run: bool = True
    approved: bool = False

    @model_validator(mode="after")
    def validate_request(self) -> SafeEditRequest:
        if not self.file_plans:
            raise ValueError("request requires at least one file plan")
        if not self.dry_run and not self.approved:
            raise ValueError("apply mode requires explicit approval")
        paths = [plan.relative_path for plan in self.file_plans]
        if len(paths) != len(set(paths)):
            raise ValueError("duplicate file plans are not allowed")
        return self


class LoadedTextFile(FrozenModel):
    """Safely loaded text-file state."""

    relative_path: str
    content: str
    encoding: str
    newline: str
    size_bytes: int = Field(ge=0)
    fingerprint: str


class FileSnapshot(FrozenModel):
    """Original state used for transaction rollback."""

    relative_path: str
    content: str
    encoding: str
    newline: str
    fingerprint: str


class FileEditResult(FrozenModel):
    """Result for one edited file."""

    relative_path: str
    original_fingerprint: str
    resulting_fingerprint: str
    unified_diff: str
    changed: bool


class EditTransactionResult(FrozenModel):
    """Atomic transaction outcome."""

    transaction_id: str
    applied: bool
    rolled_back: bool
    file_results: tuple[FileEditResult, ...]
    errors: tuple[str, ...] = ()


class SafeEditReport(FrozenModel):
    """Complete auditable output for one request."""

    request_id: str
    transaction_id: str
    dry_run: bool
    approved: bool
    file_results: tuple[FileEditResult, ...]
    validation_messages: tuple[str, ...] = ()