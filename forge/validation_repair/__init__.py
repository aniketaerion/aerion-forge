"""M3.4 Validation and Repair contracts."""

from forge.validation_repair.identifiers import (
    repair_candidate_identifier,
    repair_session_identifier,
    sha256_text,
    stable_identifier,
    validation_run_identifier,
)
from forge.validation_repair.models import (
    FindingSeverity,
    RepairAttempt,
    RepairCandidate,
    RepairReport,
    RepairSession,
    RepairStatus,
    ValidationCommand,
    ValidationFinding,
    ValidationRun,
    ValidationStatus,
    ValidationTool,
)
from forge.validation_repair.policies import ValidationRepairPolicy

__all__ = [
    "FindingSeverity",
    "RepairAttempt",
    "RepairCandidate",
    "RepairReport",
    "RepairSession",
    "RepairStatus",
    "ValidationCommand",
    "ValidationFinding",
    "ValidationRepairPolicy",
    "ValidationRun",
    "ValidationStatus",
    "ValidationTool",
    "repair_candidate_identifier",
    "repair_session_identifier",
    "sha256_text",
    "stable_identifier",
    "validation_run_identifier",
]