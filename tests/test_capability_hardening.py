"""Milestone 1.5.3 focused contract and compatibility tests."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from forge.capabilities.catalogue import built_in_catalogue
from forge.capabilities.errors import (
    CapabilityReportError,
    CapabilityStoreCorruptionError,
    CapabilityValidationError,
)
from forge.capabilities.models import (
    REGISTRY_ID,
    SCHEMA_VERSION,
    CapabilityAccessMode,
    CapabilityApprovalPolicy,
    CapabilityAvailabilityScope,
    CapabilityCategory,
    CapabilityCommand,
    CapabilityDefinition,
    CapabilityDeprecation,
    CapabilityImplementationStatus,
    CapabilityInput,
    CapabilityInputType,
    CapabilityLifecycle,
    CapabilityMaturity,
    CapabilityOutput,
    CapabilityOutputType,
    CapabilityRegistryConfiguration,
)
from forge.capabilities.query import CapabilityRegistryQuery
from forge.capabilities.registry import CapabilityRegistryBuilder
from forge.capabilities.renderer import CapabilityRegistryRenderer
from forge.capabilities.service import CapabilityRegistryService
from forge.capabilities.store import CapabilityRegistryRepository
from forge.cli import app
from forge.discovery.scanner import RepositoryDiscoveryScanner
from forge.indexing.scanner import ProjectIndexScanner

APPROVED_IDS = {
    "workspace-management",
    "repository-discovery",
    "incremental-project-index",
    "engineering-knowledge-graph",
    "capability-registry",
    "runtime-configuration",
    "runtime-health-diagnostics",
    "phase-validation-release",
    "mission-planning",
    "task-management",
    "impact-decision-engine",
    "engineering-memory",
    "mission-reporting",
    "execution-controller",
    "safe-change-planning",
    "safe-code-editing",
    "build-verification",
    "error-recovery",
    "git-review-package",
    "documentation-generation",
    "frontend-analysis",
    "backend-analysis",
    "database-migration-analysis",
    "api-contract-analysis",
    "erp-module-analysis",
    "erp-workflow-analysis",
    "erp-knowledge-model",
    "erp-mission-execution",
    "automated-test-generation",
    "regression-validation",
    "human-approval-workflow",
}
IMPLEMENTED_IDS = {
    "workspace-management",
    "repository-discovery",
    "incremental-project-index",
    "engineering-knowledge-graph",
    "capability-registry",
    "runtime-configuration",
}


def _definition(
    capability_id: str,
    *,
    required: tuple[str, ...] = (),
    optional: tuple[str, ...] = (),
    lifecycle: CapabilityLifecycle = CapabilityLifecycle.AVAILABLE,
    implementation: CapabilityImplementationStatus = CapabilityImplementationStatus.IMPLEMENTED,
    deprecation: CapabilityDeprecation | None = None,
) -> CapabilityDefinition:
    return CapabilityDefinition(
        capability_id=capability_id,
        display_name=capability_id,
        description="Contract fixture.",
        capability_version="1.0",
        forge_version="0.2",
        phase="1",
        milestone="1.5",
        category=CapabilityCategory.FOUNDATION,
        lifecycle=lifecycle,
        maturity=CapabilityMaturity.STABLE,
        implementation_status=implementation,
        required_capabilities=required,
        optional_capabilities=optional,
        access_mode=CapabilityAccessMode.READ_ONLY,
        approval_policy=CapabilityApprovalPolicy.NONE,
        availability_scope=CapabilityAvailabilityScope.GLOBAL,
        deprecation=deprecation,
    )


def _service(
    tmp_path: Path, renderer: CapabilityRegistryRenderer | None = None
) -> CapabilityRegistryService:
    return CapabilityRegistryService(
        CapabilityRegistryRepository(tmp_path / "memory" / "capabilities.json"),
        tmp_path / "reports",
        CapabilityRegistryConfiguration(),
        renderer,
    )


def test_exact_approved_catalogue_and_real_contract_paths() -> None:
    catalogue = built_in_catalogue()
    assert {item.capability_id for item in catalogue} == APPROVED_IDS
    assert {
        item.capability_id
        for item in catalogue
        if item.implementation_status is CapabilityImplementationStatus.IMPLEMENTED
    } == IMPLEMENTED_IDS
    assert sum(item.lifecycle is CapabilityLifecycle.PLANNED for item in catalogue) == 25
    root = Path(__file__).resolve().parents[1]
    assert all((root / path).is_file() for item in catalogue for path in item.documentation_paths)
    subsystem = {
        "workspace-management": "workspace",
        "repository-discovery": "discovery",
        "incremental-project-index": "indexing",
        "engineering-knowledge-graph": "knowledge",
        "capability-registry": "capabilities",
        "runtime-configuration": "configuration",
    }
    assert all((root / "forge" / subsystem[item]).is_dir() for item in IMPLEMENTED_IDS)


def test_planned_entries_are_non_executable_and_truthful() -> None:
    result = CapabilityRegistryBuilder(CapabilityRegistryConfiguration()).build(
        built_in_catalogue()
    )
    evaluations = {item.capability_id: item for item in result.registry.evaluations}
    planned = [
        item for item in result.registry.definitions if item.capability_id not in IMPLEMENTED_IDS
    ]
    assert all(
        not item.cli_commands and not item.produced_outputs and not item.required_inputs
        for item in planned
    )
    assert all(not evaluations[item.capability_id].available for item in planned)
    assert all(item.maturity is not CapabilityMaturity.STABLE for item in planned)


def test_definition_collection_order_is_canonical() -> None:
    inputs = (
        CapabilityInput(
            input_id="z", input_type=CapabilityInputType.CONFIGURATION, name="z", description="z"
        ),
        CapabilityInput(
            input_id="a", input_type=CapabilityInputType.USER_REQUEST, name="a", description="a"
        ),
    )
    outputs = (
        CapabilityOutput(
            output_id="z", output_type=CapabilityOutputType.JSON_REPORT, name="z", description="z"
        ),
        CapabilityOutput(
            output_id="a", output_type=CapabilityOutputType.CLI_OUTPUT, name="a", description="a"
        ),
    )
    commands = (
        CapabilityCommand(command="forge z", description="z"),
        CapabilityCommand(command="forge a", description="a"),
    )
    base = _definition("ordered").model_dump()
    first = CapabilityDefinition.model_validate(
        base
        | {
            "required_inputs": inputs,
            "produced_outputs": outputs,
            "cli_commands": commands,
            "tags": ("z", "a"),
        }
    )
    second = CapabilityDefinition.model_validate(
        base
        | {
            "required_inputs": tuple(reversed(inputs)),
            "produced_outputs": tuple(reversed(outputs)),
            "cli_commands": tuple(reversed(commands)),
            "tags": ("a", "z"),
        }
    )
    one = CapabilityRegistryBuilder(CapabilityRegistryConfiguration()).build((first,)).registry
    two = CapabilityRegistryBuilder(CapabilityRegistryConfiguration()).build((second,)).registry
    assert one.generation.registry_fingerprint == two.generation.registry_fingerprint


@pytest.mark.parametrize(
    "definitions",
    [
        (_definition("a", optional=("missing",)),),
        (_definition("a", required=("a",)),),
        (
            _definition("a", required=("b",)),
            _definition("b", required=("c",)),
            _definition("c", required=("a",)),
        ),
    ],
)
def test_invalid_dependency_graphs_fail(definitions: tuple[CapabilityDefinition, ...]) -> None:
    with pytest.raises(CapabilityValidationError):
        CapabilityRegistryBuilder(CapabilityRegistryConfiguration()).build(definitions)


def test_replacement_cycles_and_removed_dependencies_fail() -> None:
    a = _definition(
        "a", deprecation=CapabilityDeprecation(deprecated=True, replacement_capability_id="b")
    )
    b = _definition(
        "b", deprecation=CapabilityDeprecation(deprecated=True, replacement_capability_id="a")
    )
    with pytest.raises(CapabilityValidationError):
        CapabilityRegistryBuilder(CapabilityRegistryConfiguration()).build((a, b))
    removed = _definition(
        "removed",
        lifecycle=CapabilityLifecycle.REMOVED,
        implementation=CapabilityImplementationStatus.NOT_IMPLEMENTED,
    )
    with pytest.raises(CapabilityValidationError):
        CapabilityRegistryBuilder(CapabilityRegistryConfiguration()).build(
            (_definition("consumer", required=("removed",)), removed)
        )


def test_store_rejects_invalid_and_unsupported_schema(tmp_path: Path) -> None:
    path = tmp_path / "capabilities.json"
    store = CapabilityRegistryRepository(path)
    path.write_text("{", encoding="utf-8")
    with pytest.raises(CapabilityStoreCorruptionError):
        store.load()
    path.write_text(
        json.dumps({"schema_version": "2.0", "registry": None, "history": []}), encoding="utf-8"
    )
    with pytest.raises(CapabilityStoreCorruptionError):
        store.load()


class EscapingRenderer(CapabilityRegistryRenderer):
    def render(self, result):  # type: ignore[no-untyped-def]
        return {"../escape.json": "unsafe"}


def test_report_failure_preserves_store_and_cleans_temporary_files(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.build()
    path = tmp_path / "memory" / "capabilities.json"
    before = path.read_bytes()
    with pytest.raises(CapabilityReportError):
        _service(tmp_path, EscapingRenderer()).build()
    assert path.read_bytes() == before
    assert not list(tmp_path.rglob("*.tmp"))


def test_bounded_history_only_records_changed_generations(tmp_path: Path) -> None:
    store = CapabilityRegistryRepository(tmp_path / "capabilities.json", history_limit=1)
    base = (
        CapabilityRegistryBuilder(CapabilityRegistryConfiguration())
        .build((_definition("a"),))
        .registry
    )
    store.save(base)
    store.save(base)
    changed = (
        CapabilityRegistryBuilder(CapabilityRegistryConfiguration())
        .build((_definition("a"), _definition("b")), base)
        .registry
    )
    store.save(changed)
    assert len(store.load().history) == 1 and store.load().history[0] == base


def test_reports_are_valid_canonical_portable_and_repeatable(tmp_path: Path) -> None:
    service = _service(tmp_path)
    service.build()
    service.build()
    first = {path.name: path.read_bytes() for path in (tmp_path / "reports").iterdir()}
    service.build()
    assert first == {path.name: path.read_bytes() for path in (tmp_path / "reports").iterdir()}
    for path in (tmp_path / "reports").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    combined = b"".join(first.values())
    assert str(tmp_path).encode() not in combined and b'"timestamp"' not in combined


def test_capability_artifacts_are_excluded_by_shared_policy(tmp_path: Path) -> None:
    (tmp_path / "memory").mkdir()
    (tmp_path / "reports" / "latest").mkdir(parents=True)
    (tmp_path / "memory" / "capabilities.json").write_text("{}", encoding="utf-8")
    (tmp_path / "reports" / "latest" / "CAPABILITIES.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='fixture'\nversion='1.0'\n", encoding="utf-8"
    )
    discovery = RepositoryDiscoveryScanner(tmp_path).scan()
    _, indexed = ProjectIndexScanner(tmp_path, 1024 * 1024, 4096, 100).scan()
    paths = {item.path for item in indexed}
    assert discovery.file_count == 1 and not any(
        path.startswith(("memory/", "reports/")) for path in paths
    )


def test_query_contract_is_sorted_read_only_and_complete() -> None:
    registry = (
        CapabilityRegistryBuilder(CapabilityRegistryConfiguration())
        .build(built_in_catalogue())
        .registry
    )
    query = CapabilityRegistryQuery(registry)
    before = registry.model_dump_json()
    assert query.get_capability("capability-registry").capability_id == "capability-registry"
    assert [x.capability_id for x in query.list_capabilities()] == sorted(APPROVED_IDS)
    assert (
        len(query.list_available_capabilities()) == 6
        and len(query.list_planned_capabilities()) == 25
    )
    assert query.get_capabilities_by_category(CapabilityCategory.KNOWLEDGE)
    assert query.get_capabilities_for_project_type("React")
    assert query.get_required_capabilities("engineering-knowledge-graph")
    assert query.get_optional_capabilities("capability-registry") == ()
    assert [x.capability_id for x in query.get_dependents("workspace-management")] == sorted(
        x.capability_id for x in query.get_dependents("workspace-management")
    )
    assert query.is_available("workspace-management") and not query.is_available("mission-planning")
    assert query.get_missing_requirements("mission-planning") == ()
    assert query.get_capability_outputs("capability-registry") and query.get_capability_commands(
        "capability-registry"
    )
    assert (
        query.get_registry_summary().total_capabilities == 31
        and registry.model_dump_json() == before
    )


def test_cli_frozen_commands_and_failures(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    for args in (
        ["capabilities", "--available", "--json"],
        ["capabilities", "--planned", "--json"],
        ["capabilities", "--category", "knowledge", "--json"],
        ["capabilities", "--project-type", "React", "--json"],
        ["capabilities", "--verbose"],
        ["capability", "workspace-management"],
        ["capability", "mission-planning"],
    ):
        result = runner.invoke(app, args)
        assert result.exit_code == 0 and "Traceback" not in result.stdout
    planned = runner.invoke(app, ["capability", "mission-planning"])
    assert "not been implemented" in planned.stdout
    unknown = runner.invoke(app, ["capability", "unknown-capability"])
    assert unknown.exit_code == 2 and "Traceback" not in unknown.stdout


def test_frozen_identity_and_schema() -> None:
    result = CapabilityRegistryBuilder(CapabilityRegistryConfiguration()).build(
        built_in_catalogue()
    )
    assert result.registry.registry_id == REGISTRY_ID == "aerion-forge-capability-registry"
    assert (
        result.registry.schema_version
        == result.registry.generation.schema_version
        == SCHEMA_VERSION
        == "1.0"
    )


def test_model_rejects_absolute_documentation_path() -> None:
    with pytest.raises(ValidationError):
        CapabilityDefinition.model_validate(
            _definition("portable").model_dump() | {"documentation_paths": ("C:/private/docs.md",)}
        )
