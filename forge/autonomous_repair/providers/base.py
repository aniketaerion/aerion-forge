"""Provider contract for M3.5 Autonomous Repair."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from forge.autonomous_repair.models import (
    RepairInput,
    RepairProposal,
    RepairProviderType,
)
from forge.autonomous_repair.policies import AutonomousRepairPolicy


class AutonomousRepairProvider(ABC):
    """Base contract for bounded repair proposal providers."""

    provider_type: RepairProviderType

    @abstractmethod
    def supports(self, repair_input: RepairInput) -> bool:
        """Return whether this provider supports the input."""

    @abstractmethod
    def propose(
        self,
        repository_root: Path,
        repair_input: RepairInput,
        policy: AutonomousRepairPolicy,
    ) -> RepairProposal:
        """Produce a deterministic bounded repair proposal without mutation."""