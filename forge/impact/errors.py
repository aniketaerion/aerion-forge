"""Impact Decision Engine exception hierarchy."""


class ImpactDecisionError(Exception):
    """Base exception for Milestone 2.3."""


class ImpactValidationError(ImpactDecisionError):
    """Impact or decision contract validation failed."""


class ImpactPersistenceError(ImpactDecisionError):
    """Impact Decision persistence failed."""


class ImpactStoreCorruptionError(ImpactPersistenceError):
    """The persisted Impact Decision store is corrupt."""


class ImpactSchemaMismatchError(ImpactPersistenceError):
    """The persisted store uses an unsupported schema."""


class ImpactDecisionNotFoundError(ImpactDecisionError):
    """The requested impact assessment was not found."""


class ImpactDecisionDisabledError(ImpactDecisionError):
    """Impact Decision capability is disabled."""


class ImpactReportError(ImpactDecisionError):
    """Impact Decision report generation failed."""
