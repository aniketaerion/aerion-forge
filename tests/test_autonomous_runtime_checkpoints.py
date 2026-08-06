import pytest

from forge.autonomous_runtime.checkpoints import (
    assert_checkpoint_valid,
    verify_checkpoint,
)
from forge.autonomous_runtime.errors import MissionContractError
from forge.autonomous_runtime.models import MissionCheckpoint


def checkpoint(
    *,
    verified: bool = True,
) -> MissionCheckpoint:
    return MissionCheckpoint(
        checkpoint_id="checkpoint-1",
        mission_id="mission-1",
        step_id="step-1",
        kind="git_stash",
        repository_fingerprint="fingerprint-1",
        working_tree_digest="tree-1",
        verified=verified,
    )


def test_verified_checkpoint_passes() -> None:
    result = verify_checkpoint(
        checkpoint(),
        expected_mission_id="mission-1",
        expected_step_id="step-1",
        expected_repository_fingerprint="fingerprint-1",
    )

    assert result.valid


def test_unverified_checkpoint_is_rejected() -> None:
    with pytest.raises(MissionContractError):
        assert_checkpoint_valid(
            checkpoint(verified=False),
            expected_mission_id="mission-1",
        )