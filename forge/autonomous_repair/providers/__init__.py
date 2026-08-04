"""Built-in autonomous-repair providers."""

from forge.autonomous_repair.providers.base import AutonomousRepairProvider
from forge.autonomous_repair.providers.exact_patch import ExactPatchProvider
from forge.autonomous_repair.providers.ruff_fix import RuffFixProvider

__all__ = [
    "AutonomousRepairProvider",
    "ExactPatchProvider",
    "RuffFixProvider",
]