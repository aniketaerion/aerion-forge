"""Secret detection for memory ingestion."""

from __future__ import annotations

import re
from dataclasses import dataclass

from forge.autonomous_memory.errors import MemoryRedactionError


@dataclass(frozen=True, slots=True)
class RedactionResult:
    content: str
    detected_categories: tuple[str, ...]


_PATTERNS = (
    (
        "private_key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            re.IGNORECASE,
        ),
    ),
    (
        "bearer_token",
        re.compile(
            r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}",
            re.IGNORECASE,
        ),
    ),
    (
        "secret_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|access[_-]?token|secret|password)"
            r"\s*[:=]\s*['\"]?([^\s'\";,]{8,})"
        ),
    ),
    (
        "github_token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    ),
    (
        "aws_access_key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
)


def redact_prohibited_content(content: str) -> RedactionResult:
    redacted = content
    detected: list[str] = []

    for category, pattern in _PATTERNS:
        if pattern.search(redacted):
            detected.append(category)
            redacted = pattern.sub(
                f"[REDACTED:{category}]",
                redacted,
            )

    return RedactionResult(
        content=redacted,
        detected_categories=tuple(sorted(set(detected))),
    )


def assert_no_prohibited_content(content: str) -> None:
    result = redact_prohibited_content(content)
    if result.detected_categories:
        raise MemoryRedactionError(
            "Prohibited memory content detected: "
            + ", ".join(result.detected_categories)
        )