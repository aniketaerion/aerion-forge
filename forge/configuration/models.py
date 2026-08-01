"""Typed runtime configuration contracts."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA_VERSION = "1.0"
REDACTION = "********"


class ConfigurationSource(StrEnum):
    DEFAULT = "default"
    PROFILE = "profile"
    FILE = "file"
    COMPATIBILITY = "compatibility"
    ENVIRONMENT = "environment"
    CLI = "cli"
    UNKNOWN = "unknown"


class SettingValueType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    PATH = "path"
    ENUM = "enum"
    STRING_LIST = "string_list"
    INTEGER_LIST = "integer_list"
    DURATION = "duration"
    BYTE_SIZE = "byte_size"
    OPTIONAL_STRING = "optional_string"
    OPTIONAL_INTEGER = "optional_integer"


class ConfigurationValidationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class ConfigurationChangeType(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    REMOVED = "removed"
    UNCHANGED = "unchanged"
    SOURCE_CHANGED = "source_changed"
    PROFILE_CHANGED = "profile_changed"
    VALIDATION_CHANGED = "validation_changed"
    DEPRECATION_CHANGED = "deprecation_changed"


class RuntimeProfileName(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"
    CI = "ci"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class SettingDefinition(FrozenModel):
    key: str
    namespace: str
    name: str
    description: str
    value_type: SettingValueType
    default_value: Any = None
    required: bool = True
    sensitive: bool = False
    environment_variable: str
    compatibility_environment_variables: tuple[str, ...] = ()
    configuration_file_key: str
    allowed_values: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    pattern: str | None = None
    deprecated: bool = False
    replacement_key: str | None = None
    restart_required: bool = False
    affects_determinism: bool = True
    portable: bool = True
    introduced_version: str = "0.2"
    introduced_milestone: str = "1.6"
    tags: tuple[str, ...] = ()
    schema_version: str = SCHEMA_VERSION

    @field_validator("key")
    @classmethod
    def valid_key(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+", value):
            raise ValueError("setting key must be dotted lowercase snake-case")
        return value


class ResolvedSetting(FrozenModel):
    key: str
    value: Any = Field(default=None, exclude=True, repr=False)
    safe_value: Any = None
    value_type: SettingValueType
    source: ConfigurationSource
    source_reference: str
    default_value: Any = None
    is_default: bool
    is_overridden: bool
    sensitive: bool
    valid: bool = True
    validation_messages: tuple[str, ...] = ()
    restart_required: bool = False
    affects_determinism: bool = True
    profile: RuntimeProfileName
    schema_version: str = SCHEMA_VERSION


class ConfigurationValidationMessage(FrozenModel):
    severity: ConfigurationValidationSeverity
    key: str | None = None
    message: str


class ConfigurationValidationResult(FrozenModel):
    valid: bool = True
    messages: tuple[ConfigurationValidationMessage, ...] = ()


class ConfigurationStatistics(FrozenModel):
    total_settings: int
    by_namespace: dict[str, int]
    default_count: int
    profile_count: int
    file_count: int
    compatibility_count: int
    environment_count: int
    cli_count: int
    sensitive_count: int
    deprecated_count: int
    restart_required_count: int


class ConfigurationGeneration(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    generation_id: str
    previous_generation_id: str | None = None
    configuration_fingerprint: str
    active_profile: RuntimeProfileName
    resolved_setting_count: int
    default_count: int
    profile_count: int
    file_count: int
    compatibility_count: int
    environment_count: int
    cli_count: int
    warning_count: int
    error_count: int
    deprecated_count: int
    sensitive_count: int
    restart_required_count: int
    validation_status: str


class ConfigurationChange(FrozenModel):
    key: str
    change_type: ConfigurationChangeType
    detail: str = ""


class ConfigurationChangeSet(FrozenModel):
    added: tuple[ConfigurationChange, ...] = ()
    modified: tuple[ConfigurationChange, ...] = ()
    removed: tuple[ConfigurationChange, ...] = ()
    unchanged: tuple[ConfigurationChange, ...] = ()


class ConfigurationSnapshot(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    active_profile: RuntimeProfileName
    settings: tuple[ResolvedSetting, ...]
    validation: ConfigurationValidationResult
    statistics: ConfigurationStatistics
    configuration_fingerprint: str
    generation: ConfigurationGeneration
    changes: ConfigurationChangeSet


class ConfigurationStore(BaseModel):
    schema_version: str = SCHEMA_VERSION
    snapshot: ConfigurationSnapshot | None = None
    history: list[ConfigurationSnapshot] = Field(default_factory=list)


class ConfigurationSummary(FrozenModel):
    active_profile: RuntimeProfileName
    fingerprint: str
    generation_id: str
    total_settings: int
    overridden_settings: int
    valid: bool


class ConfigurationResult(FrozenModel):
    snapshot: ConfigurationSnapshot
