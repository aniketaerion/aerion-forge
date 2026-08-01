"""Atomic persistent JSON memory repository."""

import json
import os
import threading
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DEFAULT_MEMORY: dict[str, Any] = {
    "completed_tasks": [],
    "known_issues": [],
    "architecture_map": {},
    "dependency_graph": {},
    "project_metadata": {},
    "execution_history": [],
}


class JsonMemoryStore:
    """Thread-safe repository for durable agent memory using atomic replacement."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write(deepcopy(DEFAULT_MEMORY))

    def _read(self) -> dict[str, Any]:
        try:
            with self.path.open(encoding="utf-8") as stream:
                data = json.load(stream)
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(f"Unable to read memory store {self.path}: {exc}") from exc
        if not isinstance(data, dict):
            raise RuntimeError(f"Memory store {self.path} must contain a JSON object")
        return {**deepcopy(DEFAULT_MEMORY), **data}

    def _write(self, data: dict[str, Any]) -> None:
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as stream:
                json.dump(data, stream, indent=2, ensure_ascii=False, default=str)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.path)
        except OSError as exc:
            temporary.unlink(missing_ok=True)
            raise RuntimeError(f"Unable to write memory store {self.path}: {exc}") from exc

    def read(self, key: str | None = None) -> Any:
        """Return a defensive copy of all memory or one section."""
        with self._lock:
            data = self._read()
            return deepcopy(data if key is None else data.get(key))

    def set(self, key: str, value: Any) -> None:
        """Replace one memory section atomically."""
        with self._lock:
            data = self._read()
            data[key] = value
            self._write(data)

    def append(self, key: str, value: Any, maximum: int = 1_000) -> None:
        """Append to a bounded list section atomically."""
        with self._lock:
            data = self._read()
            values = data.setdefault(key, [])
            if not isinstance(values, list):
                raise TypeError(f"Memory section {key!r} is not a list")
            values.append(value)
            data[key] = values[-maximum:]
            self._write(data)

    def record_execution(self, action: str, status: str, details: dict[str, Any]) -> None:
        """Record a timestamped execution-history item."""
        self.append(
            "execution_history",
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "action": action,
                "status": status,
                "details": details,
            },
        )
