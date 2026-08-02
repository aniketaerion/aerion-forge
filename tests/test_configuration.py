"""Unified runtime configuration contracts and integration."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from forge.capabilities.catalogue import built_in_catalogue
from forge.cli import app
from forge.config import Settings
from forge.configuration.definitions import setting_definitions
from forge.configuration.errors import (
    ConfigurationSchemaMismatchError,
    ConfigurationValidationError,
    ConfigurationValueParseError,
)
from forge.configuration.models import ConfigurationSource, RuntimeProfileName
from forge.configuration.parsers import parse_value
from forge.configuration.query import ConfigurationQuery
from forge.configuration.resolver import ConfigurationResolver
from forge.configuration.service import ConfigurationService
from forge.configuration.store import ConfigurationRepository


def test_definitions_are_canonical_complete_and_typed() -> None:
    definitions = setting_definitions()
    keys = [x.key for x in definitions]
    assert len(definitions) == 49 and keys == sorted(keys) and len(keys) == len(set(keys))
    assert {x.namespace for x in definitions} == {
        "core",
        "workspace",
        "discovery",
        "indexing",
        "knowledge_graph",
        "capabilities",
        "reporting",
        "persistence",
        "logging",
        "security",
        "cli",
        "diagnostics",
        "planning",
    }


def test_parsers_support_required_types() -> None:
    defs = {x.key: x for x in setting_definitions()}
    assert parse_value(defs["indexing.max_file_size"], "10 MiB") == 10 * 1024 * 1024
    assert parse_value(defs["core.command_timeout"], "5m") == 300
    assert parse_value(defs["logging.verbose"], "yes") is True
    assert parse_value(defs["capabilities.disabled_ids"], "b,a") == ("a", "b")
    with pytest.raises(ConfigurationValueParseError):
        parse_value(defs["logging.verbose"], "perhaps")


def test_precedence_and_provenance(tmp_path: Path) -> None:
    config = tmp_path / "forge.toml"
    config.write_text("[indexing]\nmax_files=10\n", encoding="utf-8")
    env = {"AERION_INDEX_MAX_FILES": "20", "FORGE_INDEXING_MAX_FILES": "30"}
    snapshot = ConfigurationResolver(tmp_path).resolve(
        config_file=config, environment=env, overrides=("indexing.max_files=40",)
    )
    setting = ConfigurationQuery(snapshot).get_setting("indexing.max_files")
    assert setting.value == 40 and setting.source is ConfigurationSource.CLI
    alias = ConfigurationResolver(tmp_path).resolve(environment={"AERION_INDEX_MAX_FILES": "20"})
    assert (
        ConfigurationQuery(alias).get_source("indexing.max_files")
        is ConfigurationSource.COMPATIBILITY
    )


@pytest.mark.parametrize("profile", ["development", "test", "production", "ci"])
def test_profiles(profile: str, tmp_path: Path) -> None:
    assert ConfigurationResolver(tmp_path).resolve(
        profile=profile
    ).active_profile is RuntimeProfileName(profile)


def test_toml_strict_unknown_and_no_parent_search(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    child = parent / "child"
    child.mkdir(parents=True)
    (parent / "forge.toml").write_text('[logging]\nlevel="DEBUG"\n', encoding="utf-8")
    assert (
        ConfigurationQuery(ConfigurationResolver(child).resolve()).get_value("logging.level")
        == "INFO"
    )
    bad = child / "forge.toml"
    bad.write_text("[unknown]\nvalue=1\n", encoding="utf-8")
    with pytest.raises(ConfigurationValidationError):
        ConfigurationResolver(child).resolve()


def test_sensitive_value_never_serializes_or_fingerprints(tmp_path: Path) -> None:
    first = ConfigurationResolver(tmp_path).resolve(
        environment={"FORGE_SECURITY_API_TOKEN": "first"}
    )
    second = ConfigurationResolver(tmp_path).resolve(
        environment={"FORGE_SECURITY_API_TOKEN": "second"}
    )
    assert first.configuration_fingerprint == second.configuration_fingerprint
    for value in (first.model_dump_json(), repr(first), json.dumps(first.model_dump(mode="json"))):
        assert "first" not in value and "********" in value


def test_cross_validation_blocks_unsafe_settings(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationValidationError):
        ConfigurationResolver(tmp_path).resolve(overrides=("security.allow_shell=true",))
    with pytest.raises(ConfigurationValidationError):
        ConfigurationResolver(tmp_path).resolve(
            profile="production", overrides=("security.redact_sensitive_values=false",)
        )
    with pytest.raises(ConfigurationValidationError):
        ConfigurationResolver(tmp_path).resolve(overrides=("capabilities.disabled_ids=not-real",))


def test_service_reports_store_determinism_and_queries(tmp_path: Path) -> None:
    service = ConfigurationService(tmp_path, tmp_path / "memory", tmp_path / "reports")
    first = service.resolve().snapshot
    service.resolve()
    files = {p.name: p.read_bytes() for p in (tmp_path / "reports").iterdir()}
    third = service.resolve().snapshot
    assert first.configuration_fingerprint == third.configuration_fingerprint
    assert files == {p.name: p.read_bytes() for p in (tmp_path / "reports").iterdir()}
    assert (
        len(files) == 6
        and b"configuration" in (tmp_path / "memory" / "configuration.json").read_bytes()
    )
    query = ConfigurationQuery(third)
    assert query.get_setting("indexing.max_files")
    assert query.list_settings_by_namespace("indexing")
    assert query.list_sensitive_settings()
    assert query.list_restart_required_settings()
    assert query.get_configuration_summary().valid


def test_store_schema_and_facade_compatibility(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "configuration.json"
    path.write_text('{"schema_version":"2.0","snapshot":null,"history":[]}', encoding="utf-8")
    with pytest.raises(ConfigurationSchemaMismatchError):
        ConfigurationRepository(path).load()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FORGE_INDEXING_MAX_FILES", "123")
    assert Settings.from_runtime().index_max_files == 123


def test_cli_and_capability_promotion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    for args in (
        ["config", "show"],
        ["config", "show", "--json"],
        ["config", "get", "indexing.max_file_size"],
        ["config", "explain", "indexing.max_file_size"],
        ["config", "validate"],
        ["config", "profiles"],
        ["config", "fingerprint"],
    ):
        assert runner.invoke(app, args).exit_code == 0
    assert runner.invoke(app, ["config", "get", "unknown.key"]).exit_code == 2
    catalogue = {x.capability_id: x for x in built_in_catalogue()}
    assert catalogue["runtime-configuration"].implementation_status.value == "implemented"
