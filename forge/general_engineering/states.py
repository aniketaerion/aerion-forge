"""Enumerations for the M5.9 General Engineering Agent."""

from __future__ import annotations

from enum import StrEnum


class EngineeringRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceType(StrEnum):
    FILE = "file"
    SYMBOL = "symbol"
    IMPORT = "import"
    REFERENCE = "reference"
    TEST = "test"
    CONFIGURATION = "configuration"
    BUILD = "build"
    CONVENTION = "convention"
    DEPENDENCY = "dependency"
    FINGERPRINT = "fingerprint"


class EditOperationType(StrEnum):
    CREATE_FILE = "create_file"
    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"
    RENAME = "rename"


class ValidationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED_BY_APPROVED_EXCEPTION = "skipped_by_approved_exception"


class RepairDisposition(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXHAUSTED = "exhausted"


class EngineeringTerminalStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"