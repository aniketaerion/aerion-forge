"""Provider contracts for M3.7 Build Verification."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStep,
    VerificationTool,
)


class BuildVerificationProvider(ABC):
    """Base class for registered build-verification providers."""

    tool: VerificationTool

    @abstractmethod
    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        """Return a bounded argv tuple for one verification step."""

    def supports(self, tool: VerificationTool) -> bool:
        """Return whether this provider supports the requested tool."""
        return tool is self.tool