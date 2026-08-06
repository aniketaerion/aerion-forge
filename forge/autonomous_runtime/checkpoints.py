"""Checkpoint contracts and verification helpers."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.models import MissionCheckpoint


@dataclass(frozen=True, slots=True)
class CheckpointVerification:
    """Result of checkpoint verification."""

    valid: bool
    reason: str


def verify_checkpoint(
    checkpoint: MissionCheckpoint,
    *,
    expected_mission_id: str,
    expected_step_id: str | None = None,
    expected_repository_fingerprint: str | None = None,
) -> CheckpointVerification:
    """Verify checkpoint identity, ownership, and fingerprint."""
    if checkpoint.mission_id != expected_mission_id:
        return CheckpointVerification(
            valid=False,
            reason="Checkpoint belongs to another mission.",
        )

    if (
        expected_step_id is not None
        and checkpoint.step_id != expected_step_id
    ):
        return CheckpointVerification(
            valid=False,
            reason="Checkpoint belongs to another step.",
        )

    if not checkpoint.verified:
        return CheckpointVerification(
            valid=False,
            reason="Checkpoint has not been verified.",
        )

    if (
        expected_repository_fingerprint is not None
        and checkpoint.repository_fingerprint
        != expected_repository_fingerprint
    ):
        return CheckpointVerification(
            valid=False,
            reason="Checkpoint repository fingerprint does not match.",
        )

    if not checkpoint.working_tree_digest:
        return CheckpointVerification(
            valid=False,
            reason="Checkpoint working-tree digest is missing.",
        )

    return CheckpointVerification(
        valid=True,
        reason="Checkpoint is valid.",
    )


def assert_checkpoint_valid(
    checkpoint: MissionCheckpoint,
    *,
    expected_mission_id: str,
    expected_step_id: str | None = None,
    expected_repository_fingerprint: str | None = None,
) -> None:
    """Raise when a checkpoint cannot be used for recovery."""
    result = verify_checkpoint(
        checkpoint,
        expected_mission_id=expected_mission_id,
        expected_step_id=expected_step_id,
        expected_repository_fingerprint=(
            expected_repository_fingerprint
        ),
    )

    if not result.valid:
        raise MissionContractError(result.reason)