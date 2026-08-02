"""Atomic mission-plan persistence with bounded history."""

import json
import os
from pathlib import Path

from pydantic import ValidationError

from forge.planning.errors import (
    MissionPersistenceError,
    MissionSchemaMismatchError,
    MissionStoreCorruptionError,
)
from forge.planning.models import (
    SCHEMA_VERSION,
    MissionPlan,
    MissionPlanStore,
)


class MissionPlanRepository:
    """Persist validated mission plans without partial replacement."""

    def __init__(
        self,
        path: Path,
        history_limit: int = 5,
    ) -> None:
        self.path = path
        self.history_limit = history_limit

    def load(self) -> MissionPlanStore:
        if not self.path.exists():
            return MissionPlanStore()

        try:
            raw = json.loads(
                self.path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise MissionStoreCorruptionError(
                "Mission store is corrupt."
            ) from exc

        if not isinstance(raw, dict):
            raise MissionStoreCorruptionError(
                "Mission store root must be an object."
            )

        schema_version = raw.get("schema_version")

        if schema_version != SCHEMA_VERSION:
            raise MissionSchemaMismatchError(
                "Unsupported mission schema: "
                f"{schema_version or 'missing'}"
            )

        try:
            return MissionPlanStore.model_validate(raw)
        except ValidationError as exc:
            raise MissionStoreCorruptionError(
                "Mission store is invalid."
            ) from exc

    def save(self, plan: MissionPlan) -> None:
        previous = self.load()

        missions = {
            key: value.model_copy(deep=True)
            for key, value in previous.missions.items()
        }
        history = {
            key: [
                item.model_copy(deep=True)
                for item in values
            ]
            for key, values in previous.history.items()
        }

        old = missions.get(plan.mission_id)

        if (
            old is not None
            and old.mission_fingerprint
            != plan.mission_fingerprint
        ):
            history.setdefault(
                plan.mission_id,
                [],
            ).append(old.model_copy(deep=True))

        if self.history_limit:
            history[plan.mission_id] = history.get(
                plan.mission_id,
                [],
            )[-self.history_limit :]
        else:
            history[plan.mission_id] = []

        missions[plan.mission_id] = plan.model_copy(deep=True)

        store = MissionPlanStore(
            missions=missions,
            history=history,
        )

        content = (
            json.dumps(
                store.model_dump(mode="json"),
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )

        self._atomic_write(content.encode("utf-8"))

    def snapshot_bytes(self) -> bytes | None:
        """Return current store bytes for rollback."""

        if not self.path.exists():
            return None

        try:
            return self.path.read_bytes()
        except OSError as exc:
            raise MissionPersistenceError(
                "Unable to snapshot the mission store."
            ) from exc

    def restore_bytes(
        self,
        snapshot: bytes | None,
    ) -> None:
        """Restore previous bytes or remove a newly created store."""

        if snapshot is None:
            try:
                self.path.unlink(missing_ok=True)
            except OSError as exc:
                raise MissionPersistenceError(
                    "Unable to remove the new mission store."
                ) from exc
            return

        self._atomic_write(snapshot)

    def _atomic_write(self, content: bytes) -> None:
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = self.path.with_suffix(
            self.path.suffix + ".tmp"
        )

        try:
            with temporary.open("wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())

            temporary.replace(self.path)

        except OSError as exc:
            temporary.unlink(missing_ok=True)

            raise MissionPersistenceError(
                "Unable to persist the mission store."
            ) from exc
