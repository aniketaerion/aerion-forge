"""Typed errors for autonomous memory and learning."""

class AutonomousMemoryError(RuntimeError):
    """Base error for autonomous-memory failures."""


class MemoryContractError(AutonomousMemoryError):
    """Raised when a memory contract is invalid."""


class MemoryIdentifierError(AutonomousMemoryError):
    """Raised when a stable identifier cannot be created."""


class MemoryPolicyError(AutonomousMemoryError):
    """Raised when memory policy is unsafe."""


class MemoryRedactionError(AutonomousMemoryError):
    """Raised when prohibited content is detected."""


class MemorySupersessionError(AutonomousMemoryError):
    """Raised when supersession is invalid."""


class MemoryScopeError(AutonomousMemoryError):
    """Raised when memory crosses an invalid scope."""