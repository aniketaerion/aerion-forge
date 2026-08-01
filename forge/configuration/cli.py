"""Typer commands for unified runtime configuration inspection."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.config import Settings
from forge.configuration.errors import (
    ConfigurationError,
    ConfigurationFileNotFoundError,
    ConfigurationFileParseError,
    ConfigurationKeyNotFoundError,
    ConfigurationPersistenceError,
    ConfigurationProfileNotFoundError,
    ConfigurationReportError,
    ConfigurationSchemaMismatchError,
    ConfigurationStoreCorruptionError,
    ConfigurationValidationError,
    ConfigurationValueParseError,
)
from forge.configuration.models import ConfigurationSnapshot
from forge.configuration.profiles import PROFILE_DESCRIPTIONS, PROFILES
from forge.configuration.query import ConfigurationQuery
from forge.configuration.service import ConfigurationService

config_app = typer.Typer(
    help="Inspect and validate unified Forge runtime configuration.",
    no_args_is_help=True,
)
console = Console()


def _service() -> ConfigurationService:
    settings = Settings.from_runtime()
    return ConfigurationService(
        Path.cwd(),
        settings.memory_path,
        settings.reports_path,
    )


def _resolve(
    profile: str | None,
    config: Path | None,
    values: list[str],
    persist: bool = True,
) -> ConfigurationSnapshot:
    return (
        _service()
        .resolve(
            profile=profile,
            config_file=config,
            overrides=tuple(values),
            persist=persist,
        )
        .snapshot
    )


def _exit(exc: ConfigurationError) -> int:
    if isinstance(
        exc,
        ConfigurationKeyNotFoundError | ConfigurationProfileNotFoundError,
    ):
        return 2

    if isinstance(
        exc,
        ConfigurationFileNotFoundError | ConfigurationFileParseError,
    ):
        return 3

    if isinstance(exc, ConfigurationValueParseError):
        return 4

    if isinstance(exc, ConfigurationValidationError):
        return 5

    if isinstance(exc, ConfigurationPersistenceError):
        return 6

    if isinstance(exc, ConfigurationReportError):
        return 7

    if isinstance(exc, ConfigurationStoreCorruptionError):
        return 8

    if isinstance(exc, ConfigurationSchemaMismatchError):
        return 9

    return 2


def _common(
    profile: str | None,
    config: Path | None,
    values: list[str],
    persist: bool = True,
) -> ConfigurationSnapshot:
    try:
        return _resolve(profile, config, values, persist)
    except ConfigurationError as exc:
        console.print(f"[bold red]Configuration error:[/bold red] {exc}")
        raise typer.Exit(code=_exit(exc)) from exc


@config_app.command("show")
def show(
    json_output: Annotated[bool, typer.Option("--json")] = False,
    sources: Annotated[bool, typer.Option("--sources")] = False,
    overrides_only: Annotated[bool, typer.Option("--overrides")] = False,
    namespace: Annotated[str | None, typer.Option("--namespace")] = None,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    set_values: Annotated[list[str] | None, typer.Option("--set")] = None,
) -> None:
    snapshot = _common(profile, config, set_values or [])
    query = ConfigurationQuery(snapshot)

    settings = (
        query.list_settings_by_namespace(namespace)
        if namespace
        else query.list_settings()
    )

    if namespace and not settings:
        console.print(f"[bold red]Unknown namespace:[/bold red] {namespace}")
        raise typer.Exit(code=2)

    if overrides_only:
        settings = tuple(setting for setting in settings if setting.is_overridden)

    if json_output:
        console.print_json(
            json.dumps(
                {
                    "active_profile": snapshot.active_profile,
                    "fingerprint": snapshot.configuration_fingerprint,
                    "settings": [
                        setting.model_dump(mode="json") for setting in settings
                    ],
                },
                sort_keys=True,
                default=str,
            )
        )
        return

    table = Table(title="Forge Runtime Configuration")

    for name in (
        "Key",
        "Value",
        "Source",
        "Profile",
        "State",
        "Sensitive",
        "Valid",
    ):
        table.add_column(name)

    for setting in settings:
        table.add_row(
            setting.key,
            str(setting.safe_value),
            setting.source.value,
            setting.profile.value,
            "default" if setting.is_default else "override",
            "yes" if setting.sensitive else "no",
            "yes" if setting.valid else "no",
        )

    console.print(table)


@config_app.command("get")
def get(
    key: str,
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    set_values: Annotated[list[str] | None, typer.Option("--set")] = None,
) -> None:
    try:
        value = ConfigurationQuery(
            _common(profile, config, set_values or [])
        ).get_safe_value(key)
        console.print(value)
    except ConfigurationKeyNotFoundError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=2) from exc


@config_app.command("explain")
def explain(key: str) -> None:
    try:
        definition, setting = ConfigurationQuery(
            _common(None, None, [])
        ).explain_setting(key)
    except ConfigurationKeyNotFoundError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(code=2) from exc

    console.print_json(
        json.dumps(
            {
                "definition": definition.model_dump(mode="json"),
                "resolved": setting.model_dump(mode="json"),
            },
            sort_keys=True,
            default=str,
        )
    )


@config_app.command("validate")
def validate(
    profile: Annotated[str | None, typer.Option("--profile")] = None,
    config: Annotated[Path | None, typer.Option("--config")] = None,
    set_values: Annotated[list[str] | None, typer.Option("--set")] = None,
) -> None:
    snapshot = _common(
        profile,
        config,
        set_values or [],
        persist=False,
    )

    console.print(
        "Configuration valid"
        if snapshot.validation.valid
        else "Configuration invalid"
    )


@config_app.command("profiles")
def profiles() -> None:
    for profile in sorted(PROFILES, key=lambda item: item.value):
        console.print(
            f"{profile.value}: {PROFILE_DESCRIPTIONS[profile]}"
        )


@config_app.command("fingerprint")
def fingerprint() -> None:
    snapshot = _common(None, None, [])

    console.print(
        f"{snapshot.configuration_fingerprint}\n"
        f"{snapshot.generation.generation_id}"
    )
