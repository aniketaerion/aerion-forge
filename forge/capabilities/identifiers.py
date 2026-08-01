"""Canonical hashing helpers for capability registry state."""

import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()
