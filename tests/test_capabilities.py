"""Capability registry model, evaluation, persistence, report, and query tests."""

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from forge.capabilities.catalogue import built_in_catalogue
from forge.capabilities.errors import (
    CapabilityNotFoundError,
    CapabilityStoreCorruptionError,
    CapabilityValidationError,
)
from forge.capabilities.models import (
    CapabilityAccessMode,
    CapabilityApprovalPolicy,
    CapabilityAvailabilityScope,
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityImplementationStatus,
    CapabilityLifecycle,
    CapabilityMaturity,
    CapabilityRegistryConfiguration,
    CapabilityRegistryResult,
)
from forge.capabilities.query import CapabilityRegistryQuery
from forge.capabilities.registry import CapabilityRegistryBuilder
from forge.capabilities.service import CapabilityRegistryService
from forge.capabilities.store import CapabilityRegistryRepository
from forge.cli import app


def _build(
    configuration: CapabilityRegistryConfiguration | None = None,
) -> CapabilityRegistryResult:
    return CapabilityRegistryBuilder(configuration or CapabilityRegistryConfiguration()).build(
        built_in_catalogue()
    )


def _definition(capability_id: str, requires: tuple[str, ...] = ()) -> CapabilityDefinition:
    return CapabilityDefinition(
        capability_id=capability_id,
        display_name=capability_id,
        description="Test capability.",
        capability_version="1.0",
        forge_version="0.2",
        phase="1",
        milestone="1.5",
        category=CapabilityCategory.FOUNDATION,
        lifecycle=CapabilityLifecycle.AVAILABLE,
        maturity=CapabilityMaturity.STABLE,
        implementation_status=CapabilityImplementationStatus.IMPLEMENTED,
        required_capabilities=requires,
        access_mode=CapabilityAccessMode.READ_ONLY,
        approval_policy=CapabilityApprovalPolicy.NONE,
        availability_scope=CapabilityAvailabilityScope.GLOBAL,
    )


def test_catalogue_is_complete_unique_and_truthful() -> None:
    catalogue = built_in_catalogue()
    ids = [x.capability_id for x in catalogue]
    assert len(catalogue) == 31 and ids == sorted(ids) and len(ids) == len(set(ids))
    completed = {
        "workspace-management",
        "repository-discovery",
        "incremental-project-index",
        "engineering-knowledge-graph",
        "capability-registry",
    }
    assert completed <= set(ids)
    assert all(
        x.implementation_status is CapabilityImplementationStatus.IMPLEMENTED
        for x in catalogue
        if x.capability_id in completed
    )
    assert all(
        x.lifecycle is CapabilityLifecycle.PLANNED
        for x in catalogue
        if x.capability_id not in completed
    )
    mutating = [x for x in catalogue if x.access_mode is CapabilityAccessMode.TARGET_MUTATING]
    assert mutating and all(
        x.approval_policy is not CapabilityApprovalPolicy.NONE for x in mutating
    )


def test_invalid_definition_contracts() -> None:
    with pytest.raises(ValidationError):
        _definition("Not Valid")
    with pytest.raises(ValidationError):
        _definition("valid-id").model_copy(
            update={"forge_version": "tomorrow"}, deep=True
        ).__class__.model_validate(
            _definition("valid-id").model_dump() | {"forge_version": "tomorrow"}
        )


def test_dependency_cycles_and_unknown_dependencies_fail() -> None:
    with pytest.raises(CapabilityValidationError):
        CapabilityRegistryBuilder(CapabilityRegistryConfiguration()).build(
            (_definition("a", ("b",)),)
        )
    with pytest.raises(CapabilityValidationError):
        CapabilityRegistryBuilder(CapabilityRegistryConfiguration()).build(
            (_definition("a", ("b",)), _definition("b", ("a",)))
        )


def test_disabled_dependency_propagates() -> None:
    result = _build(CapabilityRegistryConfiguration(disabled_ids=("workspace-management",)))
    query = CapabilityRegistryQuery(result.registry)
    assert not query.is_available("workspace-management")
    assert not query.is_available("repository-discovery")
    assert "workspace-management" in query.get_missing_requirements("repository-discovery")


def test_unknown_disabled_id_strict_and_non_strict() -> None:
    with pytest.raises(CapabilityValidationError):
        _build(CapabilityRegistryConfiguration(disabled_ids=("missing",)))
    result = _build(
        CapabilityRegistryConfiguration(disabled_ids=("missing",), strict_validation=False)
    )
    assert result.registry.statistics.available_capabilities == 5


def test_deterministic_build_and_query_api() -> None:
    first = _build().registry
    second = _build().registry
    assert first.generation == second.generation
    query = CapabilityRegistryQuery(first)
    assert len(query.list_available_capabilities()) == 5
    assert len(query.list_planned_capabilities()) == 26
    assert query.get_capabilities_by_category(CapabilityCategory.KNOWLEDGE)
    assert query.get_capabilities_for_project_type("React")
    assert query.get_required_capabilities("engineering-knowledge-graph")
    assert query.get_dependents("workspace-management")
    assert query.get_capability_outputs("capability-registry")
    assert query.get_capability_commands("capability-registry")
    with pytest.raises(CapabilityNotFoundError):
        query.get_capability("knowledge-graph")


def test_store_reports_and_corruption(tmp_path: Path) -> None:
    store = CapabilityRegistryRepository(tmp_path / "memory" / "capabilities.json", history_limit=1)
    service = CapabilityRegistryService(
        store, tmp_path / "reports", CapabilityRegistryConfiguration()
    )
    first = service.build()
    first_bytes = store.path.read_bytes()
    second = service.build()
    assert (
        first.registry.generation == second.registry.generation
        and first_bytes == store.path.read_bytes()
    )
    reports = {x.name: x.read_bytes() for x in (tmp_path / "reports").iterdir()}
    service.build()
    assert reports == {x.name: x.read_bytes() for x in (tmp_path / "reports").iterdir()}
    assert {
        "CAPABILITIES.json",
        "CAPABILITY_SUMMARY.json",
        "CAPABILITY_CHANGES.json",
        "CAPABILITY_DEPENDENCIES.json",
        "CAPABILITY_SUMMARY.md",
        "CAPABILITY_CHANGES.md",
    } <= set(reports)
    assert str(tmp_path).encode() not in b"".join(reports.values())
    store.path.write_text("not-json", encoding="utf-8")
    with pytest.raises(CapabilityStoreCorruptionError):
        store.load()


def test_cli_list_detail_filters_and_unknown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["capabilities"]).exit_code == 0
    planned = runner.invoke(app, ["capabilities", "--planned", "--category", "planning", "--json"])
    assert planned.exit_code == 0 and "mission-planning" in planned.stdout
    detail = runner.invoke(app, ["capability", "capability-registry", "--json"])
    assert detail.exit_code == 0 and '"available": true' in detail.stdout
    assert runner.invoke(app, ["capability", "knowledge-graph"]).exit_code == 2


def test_report_hash_is_repeatable(tmp_path: Path) -> None:
    service = CapabilityRegistryService(
        CapabilityRegistryRepository(tmp_path / "state.json"),
        tmp_path / "reports",
        CapabilityRegistryConfiguration(),
    )
    service.build()
    first = hashlib.sha256((tmp_path / "reports" / "CAPABILITIES.json").read_bytes()).hexdigest()
    service.build()
    second = hashlib.sha256((tmp_path / "reports" / "CAPABILITIES.json").read_bytes()).hexdigest()
    assert first == second
