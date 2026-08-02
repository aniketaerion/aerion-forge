"""Deterministic identifiers and fingerprints for Task Management."""

import hashlib
import json
import re
from typing import Any

from forge.tasks.errors import TaskIdentifierError
from forge.tasks.models import (
    SCHEMA_VERSION,
    EngineeringTask,
    TaskSet,
)

TASK_POLICY_VERSION = "1.0"
TASK_ID_PATTERN = re.compile(r"^task-[0-9a-f]{20}$")
FINGERPRINT_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json(value: Any) -> str:
    """Serialize a value into canonical deterministic JSON."""

    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        default=str,
    )


def canonical_hash(value: Any) -> str:
    """Return a deterministic SHA-256 hash."""

    return hashlib.sha256(
        _canonical_json(value).encode("utf-8")
    ).hexdigest()


def normalize_task_title(title: str) -> str:
    """Normalize a task title for stable identity generation."""

    normalized = " ".join(title.strip().casefold().split())

    if not normalized:
        raise TaskIdentifierError(
            "Task title cannot be blank during identifier generation."
        )

    return normalized


def build_task_id(
    *,
    mission_id: str,
    workstream_id: str,
    parent_task_id: str | None,
    title: str,
    sequence: int,
) -> str:
    """Build a stable task identifier from canonical identity fields."""

    if not mission_id.strip():
        raise TaskIdentifierError("mission_id cannot be blank.")

    if not workstream_id.strip():
        raise TaskIdentifierError("workstream_id cannot be blank.")

    if sequence < 0:
        raise TaskIdentifierError("sequence cannot be negative.")

    identity = {
        "schema_version": SCHEMA_VERSION,
        "policy_version": TASK_POLICY_VERSION,
        "mission_id": mission_id.strip(),
        "workstream_id": workstream_id.strip(),
        "parent_task_id": (
            parent_task_id.strip()
            if parent_task_id is not None
            else None
        ),
        "title": normalize_task_title(title),
        "sequence": sequence,
    }

    return f"task-{canonical_hash(identity)[:20]}"


def task_fingerprint_payload(
    task: EngineeringTask,
) -> dict[str, Any]:
    """Return canonical task content excluding its own fingerprint."""

    payload = task.model_dump(mode="json")
    payload["task_fingerprint"] = ""

    return payload


def build_task_fingerprint(
    task: EngineeringTask,
) -> str:
    """Build a deterministic fingerprint for one task."""

    return canonical_hash(task_fingerprint_payload(task))


def validate_task_id(task_id: str) -> bool:
    """Return whether a task identifier matches the public contract."""

    return bool(TASK_ID_PATTERN.fullmatch(task_id))


def validate_fingerprint(fingerprint: str) -> bool:
    """Return whether a fingerprint is canonical SHA-256 hexadecimal."""

    return bool(FINGERPRINT_PATTERN.fullmatch(fingerprint))


def task_set_fingerprint_payload(
    task_set: TaskSet,
) -> dict[str, Any]:
    """Return canonical task-set content excluding its fingerprint."""

    payload = task_set.model_dump(mode="json")
    payload["task_set_fingerprint"] = ""
    payload["tasks"] = sorted(
        payload["tasks"],
        key=lambda item: (
            item["sequence"],
            item["task_id"],
        ),
    )
    payload["source_fingerprints"] = dict(
        sorted(payload["source_fingerprints"].items())
    )
    return payload


def build_task_set_fingerprint(
    task_set: TaskSet,
) -> str:
    """Build a deterministic fingerprint for a task set."""

    return canonical_hash(
        task_set_fingerprint_payload(task_set)
    )
