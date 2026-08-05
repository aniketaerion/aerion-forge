"""Typed errors for M3.7 Build Verification."""


class BuildVerificationError(Exception):
    """Base error for build verification."""


class BuildVerificationConfigurationError(BuildVerificationError):
    """Raised when build verification configuration is invalid."""


class BuildVerificationPolicyError(BuildVerificationError):
    """Raised when a request violates a verification policy."""


class BuildVerificationValidationError(BuildVerificationError):
    """Raised when verification evidence is invalid."""


class BuildVerificationProviderError(BuildVerificationError):
    """Raised when a build provider cannot execute safely."""


class BuildVerificationTimeoutError(BuildVerificationProviderError):
    """Raised when a verification command exceeds its timeout."""


class BuildVerificationPersistenceError(BuildVerificationError):
    """Raised when verification evidence cannot be persisted."""


class BuildVerificationReportError(BuildVerificationError):
    """Raised when a verification report cannot be written."""


class BuildVerificationNotFoundError(BuildVerificationError):
    """Raised when requested verification evidence does not exist."""


class BuildVerificationStateError(BuildVerificationError):
    """Raised when the verification state transition is invalid."""