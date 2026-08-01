"""Unified runtime configuration exception hierarchy."""


class ConfigurationError(Exception):
    pass


class ConfigurationKeyNotFoundError(ConfigurationError):
    pass


class ConfigurationProfileNotFoundError(ConfigurationError):
    pass


class ConfigurationFileNotFoundError(ConfigurationError):
    pass


class ConfigurationFileParseError(ConfigurationError):
    pass


class ConfigurationValueParseError(ConfigurationError):
    pass


class ConfigurationValidationError(ConfigurationError):
    pass


class ConfigurationConflictError(ConfigurationError):
    pass


class ConfigurationPersistenceError(ConfigurationError):
    pass


class ConfigurationReportError(ConfigurationError):
    pass


class ConfigurationStoreCorruptionError(ConfigurationPersistenceError):
    pass


class ConfigurationSchemaMismatchError(ConfigurationStoreCorruptionError):
    pass
