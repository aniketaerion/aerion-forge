"""Explicit TOML and known-environment input loading."""

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.configuration.errors import ConfigurationFileNotFoundError, ConfigurationFileParseError
from forge.configuration.models import SettingDefinition


def select_config_file(
    root: Path, explicit: Path | None, environment: Mapping[str, str]
) -> Path | None:
    if explicit is not None:
        if not explicit.is_file():
            raise ConfigurationFileNotFoundError(f"Configuration file not found: {explicit.name}")
        return explicit
    if environment.get("FORGE_CONFIG_FILE"):
        path = Path(environment["FORGE_CONFIG_FILE"])
        if not path.is_file():
            raise ConfigurationFileNotFoundError(f"Configuration file not found: {path.name}")
        return path
    for name in ("forge.toml", ".forge.toml"):
        path = root / name
        if path.is_file():
            return path
    return None


def load_toml(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationFileParseError(
            f"Unable to parse configuration file {path.name}"
        ) from exc
    return {
        f"{section}.{key}": value
        for section, values in data.items()
        if isinstance(values, dict)
        for key, value in values.items()
    }


def known_environment(
    definitions: tuple[SettingDefinition, ...], environment: Mapping[str, str] | None = None
) -> dict[str, str]:
    source = os.environ if environment is None else environment
    names = (
        {d.environment_variable for d in definitions}
        | {x for d in definitions for x in d.compatibility_environment_variables}
        | {"FORGE_PROFILE", "FORGE_CONFIG_FILE"}
    )
    return {name: source[name] for name in sorted(names) if name in source}
