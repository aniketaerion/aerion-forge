"""Deterministic precedence resolution, validation, and safe snapshots."""

import hashlib
import json
from collections import Counter
from collections.abc import Mapping
from pathlib import Path, PurePath

from forge.configuration.definitions import setting_definitions
from forge.configuration.errors import ConfigurationValidationError
from forge.configuration.loader import known_environment, load_toml, select_config_file
from forge.configuration.models import (
    REDACTION,
    SCHEMA_VERSION,
    ConfigurationChange,
    ConfigurationChangeSet,
    ConfigurationChangeType,
    ConfigurationGeneration,
    ConfigurationSnapshot,
    ConfigurationSource,
    ConfigurationStatistics,
    ConfigurationValidationMessage,
    ConfigurationValidationResult,
    ConfigurationValidationSeverity,
    ResolvedSetting,
    RuntimeProfileName,
)
from forge.configuration.parsers import parse_value
from forge.configuration.profiles import PROFILES, get_profile


class ConfigurationResolver:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def resolve(
        self,
        *,
        profile: str | None = None,
        config_file: Path | None = None,
        environment: Mapping[str, str] | None = None,
        overrides: tuple[str, ...] = (),
        previous: ConfigurationSnapshot | None = None,
    ) -> ConfigurationSnapshot:
        definitions = setting_definitions()
        by_key = {d.key: d for d in definitions}
        env = known_environment(definitions, environment)
        selected_file = select_config_file(self.root, config_file, env)
        file_values = load_toml(selected_file)
        profile_name = get_profile(
            profile
            or env.get("FORGE_PROFILE")
            or str(file_values.get("core.profile", "development"))
        )
        values = {d.key: d.default_value for d in definitions}
        sources = {d.key: (ConfigurationSource.DEFAULT, "built-in default") for d in definitions}
        messages: list[ConfigurationValidationMessage] = []
        for key, value in PROFILES[profile_name].items():
            values[key] = value
            sources[key] = (ConfigurationSource.PROFILE, profile_name.value)
        strict_raw = file_values.get("core.strict_validation", values["core.strict_validation"])
        strict = bool(parse_value(by_key["core.strict_validation"], strict_raw))
        for key in sorted(file_values):
            if key not in by_key:
                message = ConfigurationValidationMessage(
                    severity=ConfigurationValidationSeverity.ERROR
                    if strict
                    else ConfigurationValidationSeverity.WARNING,
                    key=key,
                    message="Unknown configuration-file setting.",
                )
                messages.append(message)
                continue
            values[key] = file_values[key]
            sources[key] = (
                ConfigurationSource.FILE,
                selected_file.name if selected_file else "configuration file",
            )
        for definition in definitions:
            aliases = [
                name for name in definition.compatibility_environment_variables if name in env
            ]
            if aliases:
                alias = sorted(aliases)[-1]
                values[definition.key] = env[alias]
                sources[definition.key] = (ConfigurationSource.COMPATIBILITY, alias)
            if definition.environment_variable in env:
                if aliases:
                    messages.append(
                        ConfigurationValidationMessage(
                            severity=ConfigurationValidationSeverity.WARNING,
                            key=definition.key,
                            message="Canonical environment variable overrides compatibility alias.",
                        )
                    )
                values[definition.key] = env[definition.environment_variable]
                sources[definition.key] = (
                    ConfigurationSource.ENVIRONMENT,
                    definition.environment_variable,
                )
        cli: dict[str, str] = {}
        for item in overrides:
            if "=" not in item:
                raise ConfigurationValidationError("CLI override must use key=value")
            key, value = item.split("=", 1)
            cli[key.strip()] = value
        for key in sorted(cli):
            if key not in by_key:
                raise ConfigurationValidationError(f"Unknown configuration key: {key}")
            values[key] = cli[key]
            sources[key] = (ConfigurationSource.CLI, "--set")
        resolved = []
        for definition in definitions:
            value = parse_value(definition, values[definition.key])
            source, reference = sources[definition.key]
            safe = REDACTION if definition.sensitive and value not in (None, "") else value
            if definition.value_type.value == "path" and PurePath(str(value)).is_absolute():
                safe = f"<runtime-path>/{PurePath(str(value)).name}"
            resolved.append(
                ResolvedSetting(
                    key=definition.key,
                    value=value,
                    safe_value=safe,
                    value_type=definition.value_type,
                    source=source,
                    source_reference=reference,
                    default_value=definition.default_value,
                    is_default=source is ConfigurationSource.DEFAULT,
                    is_overridden=source
                    not in (ConfigurationSource.DEFAULT, ConfigurationSource.PROFILE),
                    sensitive=definition.sensitive,
                    restart_required=definition.restart_required,
                    affects_determinism=definition.affects_determinism,
                    profile=profile_name,
                )
            )
        messages.extend(self._cross_validate(resolved, profile_name))
        validation = ConfigurationValidationResult(
            valid=not any(x.severity is ConfigurationValidationSeverity.ERROR for x in messages),
            messages=tuple(
                sorted(messages, key=lambda x: (x.severity.value, x.key or "", x.message))
            ),
        )
        if not validation.valid:
            raise ConfigurationValidationError(
                "Configuration validation failed: "
                + "; ".join(
                    x.message
                    for x in validation.messages
                    if x.severity is ConfigurationValidationSeverity.ERROR
                )
            )
        settings = tuple(sorted(resolved, key=lambda x: x.key))
        portable = {
            "schema_version": SCHEMA_VERSION,
            "active_profile": profile_name.value,
            "settings": [x.model_dump(mode="json") for x in settings],
        }
        fingerprint = hashlib.sha256(
            json.dumps(portable, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        generation_id = f"configuration-{fingerprint[:20]}"
        counts = Counter(x.source.value for x in settings)
        by_namespace = dict(sorted(Counter(x.key.split(".", 1)[0] for x in settings).items()))
        deprecated = sum(d.deprecated for d in definitions)
        stats = ConfigurationStatistics(
            total_settings=len(settings),
            by_namespace=by_namespace,
            default_count=counts["default"],
            profile_count=counts["profile"],
            file_count=counts["file"],
            compatibility_count=counts["compatibility"],
            environment_count=counts["environment"],
            cli_count=counts["cli"],
            sensitive_count=sum(x.sensitive for x in settings),
            deprecated_count=deprecated,
            restart_required_count=sum(x.restart_required for x in settings),
        )
        previous_id = (
            previous.generation.generation_id
            if previous and previous.configuration_fingerprint != fingerprint
            else (previous.generation.previous_generation_id if previous else None)
        )
        generation = ConfigurationGeneration(
            generation_id=generation_id,
            previous_generation_id=previous_id,
            configuration_fingerprint=fingerprint,
            active_profile=profile_name,
            resolved_setting_count=len(settings),
            default_count=stats.default_count,
            profile_count=stats.profile_count,
            file_count=stats.file_count,
            compatibility_count=stats.compatibility_count,
            environment_count=stats.environment_count,
            cli_count=stats.cli_count,
            warning_count=sum(
                x.severity is ConfigurationValidationSeverity.WARNING for x in messages
            ),
            error_count=0,
            deprecated_count=deprecated,
            sensitive_count=stats.sensitive_count,
            restart_required_count=stats.restart_required_count,
            validation_status="valid",
        )
        changes = self._diff(previous, settings)
        return ConfigurationSnapshot(
            active_profile=profile_name,
            settings=settings,
            validation=validation,
            statistics=stats,
            configuration_fingerprint=fingerprint,
            generation=generation,
            changes=changes,
        )

    def _cross_validate(
        self, settings: list[ResolvedSetting], profile: RuntimeProfileName
    ) -> list[ConfigurationValidationMessage]:
        values = {x.key: x.value for x in settings}
        messages = []
        if values["persistence.memory_directory"] == values["reporting.output_directory"]:
            messages.append(
                ConfigurationValidationMessage(
                    severity=ConfigurationValidationSeverity.ERROR,
                    message="Memory and report directories must be distinct.",
                )
            )
        for key in (
            "persistence.memory_directory",
            "reporting.output_directory",
            "workspace.store_path",
        ):
            path = PurePath(str(values[key]))
            if ".." in path.parts:
                messages.append(
                    ConfigurationValidationMessage(
                        severity=ConfigurationValidationSeverity.ERROR,
                        key=key,
                        message="Writable path must remain Forge-root-relative.",
                    )
                )
        if (
            profile is RuntimeProfileName.PRODUCTION
            and not values["security.redact_sensitive_values"]
        ):
            messages.append(
                ConfigurationValidationMessage(
                    severity=ConfigurationValidationSeverity.ERROR,
                    key="security.redact_sensitive_values",
                    message="Production requires secret redaction.",
                )
            )
        for key in ("security.allow_shell", "security.allow_docker", "security.allow_database"):
            if values[key]:
                messages.append(
                    ConfigurationValidationMessage(
                        severity=ConfigurationValidationSeverity.ERROR,
                        key=key,
                        message="Hard safety constraints cannot be enabled.",
                    )
                )
        if values["capabilities.disabled_ids"]:
            from forge.capabilities.catalogue import built_in_catalogue

            known = {x.capability_id for x in built_in_catalogue()}
            unknown = sorted(set(values["capabilities.disabled_ids"]) - known)
            if unknown:
                messages.append(
                    ConfigurationValidationMessage(
                        severity=ConfigurationValidationSeverity.ERROR,
                        key="capabilities.disabled_ids",
                        message="Unknown disabled capability ID.",
                    )
                )
        return messages

    @staticmethod
    def _diff(
        previous: ConfigurationSnapshot | None, current: tuple[ResolvedSetting, ...]
    ) -> ConfigurationChangeSet:
        old = {} if previous is None else {x.key: x for x in previous.settings}
        new = {x.key: x for x in current}
        groups: dict[str, list[ConfigurationChange]] = {
            "added": [],
            "modified": [],
            "removed": [],
            "unchanged": [],
        }
        for key in sorted(set(old) | set(new)):
            if key not in old:
                group = "added"
                kind = ConfigurationChangeType.ADDED
            elif key not in new:
                group = "removed"
                kind = ConfigurationChangeType.REMOVED
            elif old[key].model_dump() != new[key].model_dump():
                group = "modified"
                kind = ConfigurationChangeType.MODIFIED
            else:
                group = "unchanged"
                kind = ConfigurationChangeType.UNCHANGED
            observed = old.get(key) or new.get(key)
            groups[group].append(
                ConfigurationChange(
                    key=key,
                    change_type=kind,
                    detail="presence changed"
                    if observed is not None and observed.sensitive and group == "modified"
                    else "",
                )
            )
        return ConfigurationChangeSet(**{k: tuple(v) for k, v in groups.items()})
