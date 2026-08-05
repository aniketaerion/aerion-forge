"""Checkpoint persistence for M3.6 Mission Orchestration."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from forge.mission_orchestration.errors import MissionCheckpointError
from forge.mission_orchestration.models import MissionCheckpoint


class MissionCheckpointStore:
    """Persist and load immutable mission checkpoints."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    def _path(self, mission_id: str) -> Path:
        return self.root / f"{mission_id}.json"

    def save(self, checkpoint: MissionCheckpoint) -> Path:
        """Atomically persist one checkpoint."""
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            target = self._path(checkpoint.mission_id)
            temporary = target.with_suffix(".json.tmp")
            temporary.write_text(
                json.dumps(
                    checkpoint.model_dump(mode="json"),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
            temporary.replace(target)
            return target
        except OSError as exc:
            raise MissionCheckpointError(
                f"unable to save mission checkpoint: {exc}"
            ) from exc

    def load(self, mission_id: str) -> MissionCheckpoint:
        """Load one checkpoint by mission ID."""
        path = self._path(mission_id)
        try:
            return MissionCheckpoint.model_validate_json(
                path.read_text(encoding="utf-8-sig")
            )
        except (OSError, ValidationError) as exc:
            raise MissionCheckpointError(
                f"unable to load mission checkpoint {mission_id}: {exc}"
            ) from exc

    def exists(self, mission_id: str) -> bool:
        """Return whether a checkpoint exists."""
        return self._path(mission_id).is_file()

    def list_missions(self) -> tuple[str, ...]:
        """Return persisted mission IDs deterministically."""
        if not self.root.is_dir():
            return ()
        return tuple(sorted(path.stem for path in self.root.glob("*.json")))