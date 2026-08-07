"""Mission-level verification result aggregation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MissionVerificationResult:
    passed: bool
    references: tuple[str, ...]
    summary: str

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise ValueError(
                "Verification summary cannot be empty."
            )

        if self.passed and not self.references:
            raise ValueError(
                "Passed verification requires evidence references."
            )