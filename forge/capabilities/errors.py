"""Capability registry exception hierarchy."""


class CapabilityRegistryError(Exception):
    """Base error for capability registry operations."""


class CapabilityNotFoundError(CapabilityRegistryError):
    pass


class CapabilityDefinitionError(CapabilityRegistryError):
    pass


class CapabilityDependencyError(CapabilityRegistryError):
    pass


class CapabilityCycleError(CapabilityDependencyError):
    pass


class CapabilityValidationError(CapabilityRegistryError):
    pass


class CapabilityConfigurationError(CapabilityRegistryError):
    pass


class CapabilityPersistenceError(CapabilityRegistryError):
    pass


class CapabilityReportError(CapabilityRegistryError):
    pass


class CapabilityStoreCorruptionError(CapabilityPersistenceError):
    pass


class CapabilityRegistryDisabledError(CapabilityConfigurationError):
    pass
