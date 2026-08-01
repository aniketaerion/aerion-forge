"""Typed read-only configuration query API."""

from typing import Any

from forge.configuration.definitions import setting_definitions
from forge.configuration.errors import ConfigurationKeyNotFoundError
from forge.configuration.models import (
    ConfigurationSnapshot,
    ConfigurationSource,
    ConfigurationSummary,
    ConfigurationValidationResult,
    ResolvedSetting,
    RuntimeProfileName,
    SettingDefinition,
)


class ConfigurationQuery:
    def __init__(self, snapshot: ConfigurationSnapshot) -> None:
        self.snapshot = snapshot
        self._settings = {x.key: x for x in snapshot.settings}
        self._definitions = {x.key: x for x in setting_definitions()}

    def get_setting(self, key: str) -> ResolvedSetting:
        try:
            return self._settings[key]
        except KeyError as exc:
            raise ConfigurationKeyNotFoundError(f"Unknown configuration key: {key}") from exc

    def get_value(self, key: str) -> Any:
        return self.get_setting(key).value

    def get_safe_value(self, key: str) -> Any:
        return self.get_setting(key).safe_value

    def get_source(self, key: str) -> ConfigurationSource:
        return self.get_setting(key).source

    def get_definition(self, key: str) -> SettingDefinition:
        self.get_setting(key)
        return self._definitions[key]

    def list_settings(self) -> tuple[ResolvedSetting, ...]:
        return self.snapshot.settings

    def list_settings_by_namespace(self, namespace: str) -> tuple[ResolvedSetting, ...]:
        return tuple(x for x in self.snapshot.settings if x.key.startswith(namespace + "."))

    def list_overridden_settings(self) -> tuple[ResolvedSetting, ...]:
        return tuple(x for x in self.snapshot.settings if x.is_overridden)

    def list_default_settings(self) -> tuple[ResolvedSetting, ...]:
        return tuple(x for x in self.snapshot.settings if x.is_default)

    def list_sensitive_settings(self) -> tuple[ResolvedSetting, ...]:
        return tuple(x for x in self.snapshot.settings if x.sensitive)

    def list_deprecated_settings(self) -> tuple[ResolvedSetting, ...]:
        return tuple(x for x in self.snapshot.settings if self._definitions[x.key].deprecated)

    def list_restart_required_settings(self) -> tuple[ResolvedSetting, ...]:
        return tuple(x for x in self.snapshot.settings if x.restart_required)

    def get_active_profile(self) -> RuntimeProfileName:
        return self.snapshot.active_profile

    def get_configuration_fingerprint(self) -> str:
        return self.snapshot.configuration_fingerprint

    def get_validation_result(self) -> ConfigurationValidationResult:
        return self.snapshot.validation

    def explain_setting(self, key: str) -> tuple[SettingDefinition, ResolvedSetting]:
        return self.get_definition(key), self.get_setting(key)

    def get_configuration_summary(self) -> ConfigurationSummary:
        return ConfigurationSummary(
            active_profile=self.snapshot.active_profile,
            fingerprint=self.snapshot.configuration_fingerprint,
            generation_id=self.snapshot.generation.generation_id,
            total_settings=len(self.snapshot.settings),
            overridden_settings=len(self.list_overridden_settings()),
            valid=self.snapshot.validation.valid,
        )
