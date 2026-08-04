"""M3.5 Autonomous Repair contracts."""

from forge.autonomous_repair.identifiers import (
    execution_request_identifier,
    execution_session_identifier,
    patch_identifier,
    proposal_identifier,
    sha256_text,
    stable_identifier,
)
from forge.autonomous_repair.models import (
    RepairApproval,
    RepairExecutionAttempt,
    RepairExecutionReport,
    RepairExecutionRequest,
    RepairExecutionSession,
    RepairExecutionStatus,
    RepairInput,
    RepairPatch,
    RepairPatchOperation,
    RepairProposal,
    RepairProviderType,
    RepairValidationEvidence,
)
from forge.autonomous_repair.policies import AutonomousRepairPolicy

__all__ = [
    "AutonomousRepairPolicy",
    "RepairApproval",
    "RepairExecutionAttempt",
    "RepairExecutionReport",
    "RepairExecutionRequest",
    "RepairExecutionSession",
    "RepairExecutionStatus",
    "RepairInput",
    "RepairPatch",
    "RepairPatchOperation",
    "RepairProposal",
    "RepairProviderType",
    "RepairValidationEvidence",
    "execution_request_identifier",
    "execution_session_identifier",
    "patch_identifier",
    "proposal_identifier",
    "sha256_text",
    "stable_identifier",
]