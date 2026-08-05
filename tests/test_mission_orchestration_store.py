from pathlib import Path

from forge.mission_orchestration.models import (
    MissionCheckpoint,
    MissionStatus,
)
from forge.mission_orchestration.store import MissionCheckpointStore


def test_store_round_trip(tmp_path: Path) -> None:
    store = MissionCheckpointStore(tmp_path)
    checkpoint = MissionCheckpoint(
        checkpoint_id="checkpoint-1",
        mission_id="mission-1",
        workflow_id="workflow-1",
        status=MissionStatus.READY,
        repository_fingerprint="a" * 64,
    )

    store.save(checkpoint)
    loaded = store.load("mission-1")

    assert loaded == checkpoint
    assert store.exists("mission-1")


def test_store_lists_missions_deterministically(tmp_path: Path) -> None:
    store = MissionCheckpointStore(tmp_path)
    for mission_id in ("mission-b", "mission-a"):
        store.save(
            MissionCheckpoint(
                checkpoint_id=f"checkpoint-{mission_id}",
                mission_id=mission_id,
                workflow_id="workflow-1",
                status=MissionStatus.READY,
                repository_fingerprint="a" * 64,
            )
        )

    assert store.list_missions() == ("mission-a", "mission-b")