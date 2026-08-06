"""Errors raised by the autonomous planning engine."""

class AutonomousPlanningError(Exception):
    """Base error for autonomous planning."""


class PlanningContractError(AutonomousPlanningError):
    """Raised when a planning contract is invalid."""


class PlanningPolicyError(AutonomousPlanningError):
    """Raised when a plan violates policy."""


class PlanningStateError(AutonomousPlanningError):
    """Raised when a planning state transition is invalid."""


class PlanningScopeError(AutonomousPlanningError):
    """Raised when planning crosses an unauthorized scope."""