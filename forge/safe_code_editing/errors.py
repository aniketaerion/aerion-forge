"""Typed errors for safe code editing."""


class SafeCodeEditingError(RuntimeError):
    """Base error for safe code editing."""


class InvalidEditPathError(SafeCodeEditingError):
    """Raised when an edit path is invalid."""


class RepositoryPathEscapeError(SafeCodeEditingError):
    """Raised when a path resolves outside the repository root."""


class BinaryFileError(SafeCodeEditingError):
    """Raised when a binary file is supplied for text editing."""


class OversizedFileError(SafeCodeEditingError):
    """Raised when a file exceeds the configured size limit."""


class UnsupportedEncodingError(SafeCodeEditingError):
    """Raised when text encoding is unsupported."""


class FingerprintMismatchError(SafeCodeEditingError):
    """Raised when file contents changed after planning."""


class ExpectedTextMismatchError(SafeCodeEditingError):
    """Raised when expected source text does not match."""


class OverlappingOperationsError(SafeCodeEditingError):
    """Raised when edit operations overlap."""


class ApprovalRequiredError(SafeCodeEditingError):
    """Raised when apply mode lacks explicit approval."""


class SafeEditWriteError(SafeCodeEditingError):
    """Raised when an atomic file write fails."""


class SafeEditRollbackError(SafeCodeEditingError):
    """Raised when rollback cannot restore repository state."""