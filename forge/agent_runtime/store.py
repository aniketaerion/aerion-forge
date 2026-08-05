"""Persistence for M3.8 Unified Agent Runtime."""

from __future__ import annotations

import json
from pathlib import Path

from forge.agent_runtime.errors import (
    AgentRuntimePersistenceError,
)
from forge.agent_runtime.models import (
    AgentCheckpoint,
    AgentEvent,
    AgentSession,
)


class AgentRuntimeStore:
    """Persist sessions, checkpoints, and telemetry atomically."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _session_path(self, session_id: str) -> Path:
        return self.root / "sessions" / f"{session_id}.json"

    def _checkpoint_path(self, checkpoint_id: str) -> Path:
        return self.root / "checkpoints" / f"{checkpoint_id}.json"

    def _event_path(self, event_id: str) -> Path:
        return self.root / "events" / f"{event_id}.json"

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temporary.replace(path)
        except OSError as exc:
            raise AgentRuntimePersistenceError(
                f"unable to persist runtime artifact: {path}"
            ) from exc

    @staticmethod
    def _read_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise AgentRuntimePersistenceError(
                f"unable to read runtime artifact: {path}"
            ) from exc

    def save_session(self, session: AgentSession) -> Path:
        path = self._session_path(session.session_id)
        self._write_json(path, session.model_dump(mode="json"))
        return path

    def load_session(self, session_id: str) -> AgentSession:
        path = self._session_path(session_id)
        if not path.is_file():
            raise AgentRuntimePersistenceError(
                f"agent session not found: {session_id}"
            )
        return AgentSession.model_validate_json(self._read_text(path))

    def save_checkpoint(self, checkpoint: AgentCheckpoint) -> Path:
        path = self._checkpoint_path(checkpoint.checkpoint_id)
        self._write_json(path, checkpoint.model_dump(mode="json"))
        return path

    def load_checkpoint(self, checkpoint_id: str) -> AgentCheckpoint:
        path = self._checkpoint_path(checkpoint_id)
        if not path.is_file():
            raise AgentRuntimePersistenceError(
                f"agent checkpoint not found: {checkpoint_id}"
            )
        return AgentCheckpoint.model_validate_json(self._read_text(path))

    def append_event(self, event: AgentEvent) -> Path:
        path = self._event_path(event.event_id)
        self._write_json(path, event.model_dump(mode="json"))
        return path

    def list_session_ids(self) -> tuple[str, ...]:
        directory = self.root / "sessions"
        if not directory.is_dir():
            return ()
        return tuple(sorted(path.stem for path in directory.glob("*.json")))

    def list_event_ids(self) -> tuple[str, ...]:
        directory = self.root / "events"
        if not directory.is_dir():
            return ()
        return tuple(sorted(path.stem for path in directory.glob("*.json")))