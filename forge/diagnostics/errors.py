"""Explicit runtime diagnostics failures."""


class DiagnosticError(Exception):
    """Base diagnostics failure."""


class DiagnosticNotFoundError(DiagnosticError):
    pass


class DiagnosticTargetNotFoundError(DiagnosticError):
    pass


class DiagnosticDefinitionError(DiagnosticError):
    pass


class DiagnosticDependencyError(DiagnosticDefinitionError):
    pass


class DiagnosticCycleError(DiagnosticDependencyError):
    pass


class DiagnosticExecutionError(DiagnosticError):
    pass


class DiagnosticValidationError(DiagnosticError):
    pass


class DiagnosticConfigurationError(DiagnosticError):
    pass


class DiagnosticPersistenceError(DiagnosticError):
    pass


class DiagnosticReportError(DiagnosticError):
    pass


class DiagnosticStoreCorruptionError(DiagnosticPersistenceError):
    pass


class DiagnosticSchemaMismatchError(DiagnosticPersistenceError):
    pass


class DiagnosticsDisabledError(DiagnosticConfigurationError):
    pass
