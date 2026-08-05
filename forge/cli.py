"""Typer command-line interface for the local engineering platform."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge import __version__
from forge.agent_runtime.cli import agent_app
from forge.agents import RepositoryAuditAgent
from forge.autonomous_repair.cli import autonomous_repair_app
from forge.build_verification.cli import build_verification_app
from forge.capabilities import (
    CapabilityRegistryQuery,
    CapabilityRegistryRepository,
    CapabilityRegistryService,
)
from forge.capabilities.errors import (
    CapabilityNotFoundError,
    CapabilityPersistenceError,
    CapabilityRegistryDisabledError,
    CapabilityRegistryError,
    CapabilityReportError,
    CapabilityStoreCorruptionError,
    CapabilityValidationError,
)
from forge.capabilities.models import (
    CapabilityCategory,
    CapabilityDefinition,
    CapabilityEvaluation,
    CapabilityRegistryConfiguration,
    CapabilityRegistryResult,
)
from forge.config import Settings
from forge.configuration.cli import config_app
from forge.core import LoggingManager
from forge.diagnostics import DiagnosticService
from forge.diagnostics.errors import (
    DiagnosticError,
    DiagnosticNotFoundError,
    DiagnosticPersistenceError,
    DiagnosticReportError,
    DiagnosticSchemaMismatchError,
    DiagnosticsDisabledError,
    DiagnosticStoreCorruptionError,
    DiagnosticTargetNotFoundError,
    DiagnosticValidationError,
)
from forge.diagnostics.models import DiagnosticCategory, DiagnosticConfiguration, HealthStatus
from forge.discovery import DiscoveryError, DiscoveryService
from forge.domain_intelligence.api.cli import api_app
from forge.domain_intelligence.backend.cli import backend_app
from forge.domain_intelligence.database.cli import database_app
from forge.domain_intelligence.frontend.cli import frontend_app
from forge.engineering_memory.cli import memory_app
from forge.execution_controller.cli import execution_app
from forge.impact.cli import impact_app
from forge.indexing import (
    IndexConfiguration,
    IndexingError,
    IndexingService,
    IndexPersistenceError,
    IndexReportError,
    IndexTargetNotFoundError,
    ProjectIndexStore,
)
from forge.knowledge import (
    KnowledgeGraphConfiguration,
    KnowledgeGraphError,
    KnowledgeGraphInputMismatchError,
    KnowledgeGraphInputMissingError,
    KnowledgeGraphPersistenceError,
    KnowledgeGraphReportError,
    KnowledgeGraphRepository,
    KnowledgeGraphService,
    KnowledgeGraphValidationError,
)
from forge.knowledge.validator import KnowledgeGraphValidator
from forge.memory import JsonMemoryStore
from forge.mission_orchestration.cli import mission_orchestration_app
from forge.mission_reporting.cli import report_app
from forge.planning.cli import mission_app
from forge.safe_change_planning.cli import safe_change_app
from forge.safe_code_editing.cli import edit_app
from forge.tasks.cli import task_app
from forge.tools import FilesystemTool, GitTool, OllamaTool
from forge.validation_repair.cli import repair_app
from forge.workspace.cli import workspace_app
from forge.workspace.errors import WorkspaceError, WorkspaceNotFoundError
from forge.workspace.manager import WorkspaceManager

app = typer.Typer(
    name="forge",
    help="Local multi-workspace engineering platform (Version 0.2).",
    no_args_is_help=True,
)

app.add_typer(agent_app, name="agent")
console = Console()
app.add_typer(workspace_app, name="workspace")
app.add_typer(config_app, name="config")
app.add_typer(mission_app, name="mission")
app.add_typer(task_app, name="task")
app.add_typer(impact_app, name="impact")
app.add_typer(memory_app, name="memory")
app.add_typer(report_app, name="report")
app.add_typer(mission_orchestration_app, name="orchestrate")
app.add_typer(execution_app, name="execution")
app.add_typer(safe_change_app, name="safe-change")
app.add_typer(repair_app, name="repair")
app.add_typer(autonomous_repair_app, name="autonomous-repair")
app.add_typer(build_verification_app, name="verify-build")
app.add_typer(edit_app, name="edit")


app.add_typer(frontend_app, name="frontend")
app.add_typer(backend_app, name="backend")
app.add_typer(database_app, name="database")
app.add_typer(api_app, name="api")
def _capability_result(settings: Settings) -> CapabilityRegistryResult:
    configuration = CapabilityRegistryConfiguration(
        enabled=settings.capability_registry_enabled,
        disabled_ids=settings.disabled_capability_ids,
        include_planned=settings.capability_include_planned,
        strict_validation=settings.capability_strict_validation,
        history_limit=settings.capability_history_limit,
    )
    store = CapabilityRegistryRepository(
        settings.memory_path / "capabilities.json", settings.capability_history_limit
    )
    return CapabilityRegistryService(store, settings.reports_path, configuration).build()


def _capability_failure(exc: CapabilityRegistryError) -> int:
    if isinstance(exc, CapabilityRegistryDisabledError):
        return 3
    if isinstance(exc, CapabilityValidationError):
        return 5
    if isinstance(exc, CapabilityStoreCorruptionError):
        return 8
    if isinstance(exc, CapabilityPersistenceError):
        return 6
    if isinstance(exc, CapabilityReportError):
        return 7
    return 4


def _print_capability_detail(
    definition: CapabilityDefinition, evaluation: CapabilityEvaluation
) -> None:
    lines = (
        f"[bold]Capability:[/bold] {definition.capability_id}",
        f"[bold]Name:[/bold] {definition.display_name}",
        f"[bold]Status:[/bold] {evaluation.lifecycle.value}",
        f"[bold]Available:[/bold] {'yes' if evaluation.available else 'no'}",
        f"[bold]Implementation:[/bold] {definition.implementation_status.value}",
        f"[bold]Maturity:[/bold] {definition.maturity.value}",
        f"[bold]Introduced:[/bold] v{definition.forge_version} / Milestone {definition.milestone}",
        f"[bold]Requires:[/bold] {', '.join(definition.required_capabilities) or 'none'}",
        "[bold]Produces:[/bold] "
        + (", ".join(x.path_pattern or x.output_id for x in definition.produced_outputs) or "none"),
        f"[bold]Commands:[/bold] {', '.join(x.command for x in definition.cli_commands) or 'none'}",
        f"[bold]Access:[/bold] {definition.access_mode.value}",
        f"[bold]Approval:[/bold] {definition.approval_policy.value}",
        "[bold]Reason:[/bold] "
        + (", ".join(evaluation.validation_messages) or "Operational prerequisites satisfied."),
    )
    console.print("\n".join(lines))


def _settings(repository: Path | None = None, reports: Path | None = None) -> Settings:
    if repository is not None and reports is not None:
        settings = Settings.from_runtime().model_copy(
            update={"repository_path": repository.resolve(), "reports_path": reports.resolve()}
        )
    elif repository is not None:
        settings = Settings.from_runtime().model_copy(
            update={"repository_path": repository.resolve()}
        )
    elif reports is not None:
        settings = Settings.from_runtime().model_copy(update={"reports_path": reports.resolve()})
    else:
        settings = Settings.from_runtime()
    settings.ensure_runtime_directories()
    return settings


def _diagnostic_service(settings: Settings) -> DiagnosticService:
    return DiagnosticService(
        Path.cwd(),
        settings.memory_path,
        settings.reports_path,
        DiagnosticConfiguration(
            enabled=settings.diagnostics_enabled,
            strict=settings.diagnostics_strict,
            history_limit=settings.diagnostics_history_limit,
            include_optional=settings.diagnostics_include_optional,
            write_probe_enabled=settings.diagnostics_write_probe_enabled,
        ),
    )


def _diagnostic_exit(status: HealthStatus, strict: bool) -> int:
    if status is HealthStatus.UNHEALTHY:
        return 4
    if status is HealthStatus.DEGRADED:
        return 3
    if status is HealthStatus.UNKNOWN and strict:
        return 5
    return 0


def _diagnostic_category(value: str | None) -> tuple[DiagnosticCategory, ...]:
    if value is None:
        return ()
    normalized = value.replace("-", "_")
    try:
        return (DiagnosticCategory(normalized),)
    except ValueError as exc:
        raise DiagnosticNotFoundError(f"Unknown diagnostic category: {value}") from exc


def _print_diagnostics(snapshot: object, json_output: bool, summary: bool, verbose: bool) -> None:
    from forge.diagnostics.models import DiagnosticSnapshot

    if not isinstance(snapshot, DiagnosticSnapshot):
        return
    if json_output:
        console.print_json(snapshot.model_dump_json(indent=2))
        return
    totals = snapshot.summary
    console.print(f"[bold]Overall Status:[/bold] {totals.overall_status.value.upper()}")
    console.print(f"Healthy Count: {totals.healthy_count}")
    console.print(f"Degraded Count: {totals.degraded_count}")
    console.print(f"Unhealthy Count: {totals.unhealthy_count}")
    console.print(f"Unknown Count: {totals.unknown_count}")
    console.print(f"Blocking Count: {totals.blocking_count}")
    if summary:
        return
    for item in snapshot.results:
        if item.status in {HealthStatus.HEALTHY, HealthStatus.NOT_APPLICABLE} and not verbose:
            continue
        console.print(f"[bold]{item.check_id}[/bold]: {item.status.value} — {item.summary}")
        if verbose:
            for evidence in item.evidence:
                console.print(f"  {evidence.label}: {evidence.safe_value}")
            for corrective in item.corrective_actions:
                console.print(f"  Action: {corrective.command or corrective.description}")


def _run_diagnostic_cli(
    *,
    target: str | None,
    target_mode: bool,
    json_output: bool,
    summary: bool,
    verbose: bool,
    category: str | None,
    check_id: str | None,
    strict: bool,
) -> None:
    settings = _settings()
    try:
        service = _diagnostic_service(settings)
        categories = _diagnostic_category(category)
        result = (
            service.diagnose(target, categories=categories, check_id=check_id, strict=strict)
            if target_mode
            else service.health(categories=categories, check_id=check_id, strict=strict)
        )
        _print_diagnostics(result.snapshot, json_output, summary, verbose)
        code = _diagnostic_exit(result.snapshot.summary.overall_status, strict)
        if code:
            raise typer.Exit(code=code)
    except (DiagnosticNotFoundError, DiagnosticTargetNotFoundError) as exc:
        console.print(f"[bold red]Diagnostic input error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc
    except DiagnosticsDisabledError as exc:
        console.print(f"[bold red]Diagnostics disabled:[/bold red] {exc}")
        raise typer.Exit(code=6) from exc
    except DiagnosticStoreCorruptionError as exc:
        console.print(f"[bold red]Diagnostic store corrupt:[/bold red] {exc}")
        raise typer.Exit(code=11) from exc
    except DiagnosticSchemaMismatchError as exc:
        console.print(f"[bold red]Diagnostic schema error:[/bold red] {exc}")
        raise typer.Exit(code=12) from exc
    except DiagnosticReportError as exc:
        console.print(f"[bold red]Diagnostic report error:[/bold red] {exc}")
        raise typer.Exit(code=10) from exc
    except DiagnosticPersistenceError as exc:
        console.print(f"[bold red]Diagnostic persistence error:[/bold red] {exc}")
        raise typer.Exit(code=9) from exc
    except DiagnosticValidationError as exc:
        console.print(f"[bold red]Diagnostic validation error:[/bold red] {exc}")
        raise typer.Exit(code=8) from exc
    except DiagnosticError as exc:
        console.print(f"[bold red]Diagnostic failure:[/bold red] {exc}")
        raise typer.Exit(code=7) from exc


@app.command()
def health(
    json_output: Annotated[bool, typer.Option("--json")] = False,
    summary: Annotated[bool, typer.Option("--summary")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
    category: Annotated[str | None, typer.Option("--category")] = None,
    check_id: Annotated[str | None, typer.Option("--check")] = None,
    strict: Annotated[bool, typer.Option("--strict")] = False,
) -> None:
    """Diagnose the local Forge runtime."""
    _run_diagnostic_cli(
        target=None,
        target_mode=False,
        json_output=json_output,
        summary=summary,
        verbose=verbose,
        category=category,
        check_id=check_id,
        strict=strict,
    )


@app.command()
def diagnose(
    target: Annotated[
        str | None, typer.Argument(help="Workspace name, ID, or repository path.")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
    summary: Annotated[bool, typer.Option("--summary")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
    category: Annotated[str | None, typer.Option("--category")] = None,
    check_id: Annotated[str | None, typer.Option("--check")] = None,
    strict: Annotated[bool, typer.Option("--strict")] = False,
) -> None:
    """Diagnose Forge readiness for a workspace or repository."""
    _run_diagnostic_cli(
        target=target,
        target_mode=True,
        json_output=json_output,
        summary=summary,
        verbose=verbose,
        category=category,
        check_id=check_id,
        strict=strict,
    )


@app.command()
def audit(
    repository: Annotated[Path, typer.Argument(help="Repository directory to inspect.")] = Path(
        "."
    ),
    reports: Annotated[
        Path | None, typer.Option("--reports", help="Report output directory.")
    ] = None,
) -> None:
    """Perform a read-only repository audit and produce the report suite."""
    settings = _settings(repository, reports)
    logger = LoggingManager(settings.logs_path, settings.log_level).configure()
    memory = JsonMemoryStore(settings.memory_path / "knowledge.json")
    tools = {
        "filesystem": FilesystemTool(settings.repository_path),
        "git": GitTool(settings.repository_path),
        "ollama": OllamaTool(
            settings.ollama_base_url, settings.ollama_model, settings.command_timeout_seconds
        ),
    }
    agent = RepositoryAuditAgent(settings=settings, logger=logger, memory=memory, tools=tools)
    try:
        result = agent.execute(settings.repository_path)
    except Exception as exc:
        console.print(f"[bold red]Audit failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    table = Table(title="Repository Audit Complete")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Files", str(len(result.inventory.files)))
    table.add_row("Dependencies", str(len(result.dependency_graph.nodes)))
    table.add_row("Findings", str(len(result.findings)))
    table.add_row("Reports", str(len(result.reports)))
    console.print(table)
    console.print(f"Reports: [green]{settings.reports_path}[/green]")


@app.command()
def inspect(
    target: Annotated[
        str | None,
        typer.Argument(help="Workspace name, workspace ID, or repository path."),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print the complete result as JSON.")
    ] = False,
    summary: Annotated[
        bool, typer.Option("--summary", help="Print only the discovery summary.")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Print expanded discovery details.")
    ] = False,
) -> None:
    """Discover repository structure and technology metadata without source analysis."""
    settings = _settings()
    logger = LoggingManager(settings.logs_path, settings.log_level).configure()
    workspace_manager = WorkspaceManager(
        JsonMemoryStore(settings.memory_path / "workspaces.json"), logger
    )
    workspace_id: str | None = None
    try:
        if target is None:
            workspace = workspace_manager.current()
            root = workspace.repository_path if workspace else Path.cwd()
            workspace_id = workspace.workspace_id if workspace else None
        else:
            try:
                workspace = workspace_manager.load(target)
                root = workspace.repository_path
                workspace_id = workspace.workspace_id
            except WorkspaceNotFoundError:
                candidate = Path(target).expanduser()
                if not candidate.exists():
                    raise WorkspaceNotFoundError(
                        f"Workspace or repository path not found: {target}"
                    ) from None
                root = candidate
        service = DiscoveryService(
            JsonMemoryStore(settings.memory_path / "discovery.json"),
            settings.reports_path,
            logger,
        )
        result = service.inspect(root, workspace_id)
    except (DiscoveryError, WorkspaceError, OSError, RuntimeError, ValueError) as exc:
        logger.error("Repository discovery failed", extra={"context": {"error": str(exc)}})
        console.print(f"[bold red]Inspection failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(result.model_dump_json(indent=2))
        return
    console.print(f"[bold]Repository:[/bold] {result.repository_name}")
    console.print(f"[bold]Type:[/bold] {result.project_type}")
    console.print(f"[bold]Files:[/bold] {result.file_count}")
    console.print(f"[bold]Technologies:[/bold] {', '.join(result.technologies) or 'None'}")
    if verbose and not summary:
        console.print(f"[bold]Applications:[/bold] {len(result.applications)}")
        console.print(f"[bold]Dependencies:[/bold] {len(result.dependencies)}")
        console.print(f"[bold]Build systems:[/bold] {', '.join(result.build_systems) or 'None'}")
        console.print(
            f"[bold]Test frameworks:[/bold] {', '.join(result.test_frameworks) or 'None'}"
        )
        console.print(f"[bold]CI/CD:[/bold] {', '.join(result.ci_cd) or 'None'}")
    console.print(f"Reports: [green]{settings.reports_path}[/green]")


@app.command()
def index(
    target: Annotated[
        str | None,
        typer.Argument(help="Workspace name, workspace ID, or repository path."),
    ] = None,
    json_output: Annotated[
        bool, typer.Option("--json", help="Print the complete index result as JSON.")
    ] = False,
    summary: Annotated[bool, typer.Option("--summary", help="Print concise index totals.")] = False,
    changes_only: Annotated[
        bool, typer.Option("--changes", help="Print only the incremental change set.")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Print expanded indexing details.")
    ] = False,
) -> None:
    """Build or refresh the deterministic incremental project index."""
    settings = _settings()
    logger = LoggingManager(settings.logs_path, settings.log_level).configure()
    workspace_manager = WorkspaceManager(
        JsonMemoryStore(settings.memory_path / "workspaces.json"), logger
    )
    workspace_id: str | None = None
    try:
        if target is None:
            workspace = workspace_manager.current()
            root = workspace.repository_path if workspace else Path.cwd()
            workspace_id = workspace.workspace_id if workspace else None
        else:
            try:
                workspace = workspace_manager.load(target)
                root = workspace.repository_path
                workspace_id = workspace.workspace_id
            except WorkspaceNotFoundError:
                candidate = Path(target).expanduser()
                if not candidate.exists():
                    raise IndexTargetNotFoundError(
                        f"Workspace or repository path not found: {target}"
                    ) from None
                root = candidate
    except (WorkspaceError, IndexTargetNotFoundError) as exc:
        console.print(f"[bold red]Index target error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    service = IndexingService(
        ProjectIndexStore(settings.memory_path / "index.json"),
        settings.reports_path,
        logger,
        IndexConfiguration(
            max_hash_bytes=settings.index_max_hash_bytes,
            hash_chunk_bytes=settings.index_hash_chunk_bytes,
            max_files=settings.index_max_files,
        ),
    )
    try:
        result = service.index(root, workspace_id)
    except IndexReportError as exc:
        console.print(f"[bold red]Index report error:[/bold red] {exc}")
        raise typer.Exit(code=5) from exc
    except IndexPersistenceError as exc:
        console.print(f"[bold red]Index persistence error:[/bold red] {exc}")
        raise typer.Exit(code=4) from exc
    except IndexingError as exc:
        console.print(f"[bold red]Indexing failed:[/bold red] {exc}")
        raise typer.Exit(code=3) from exc

    generation = result.project_index.generation
    statistics = generation.statistics
    if changes_only:
        console.print_json(result.changes.model_dump_json(indent=2))
        return
    if json_output:
        console.print_json(result.model_dump_json(indent=2))
        return
    console.print(f"[bold]Repository:[/bold] {generation.repository_name}")
    console.print(f"[bold]Indexed files:[/bold] {statistics.total_indexed_files}")
    console.print(f"[bold]State:[/bold] {generation.repository_state_fingerprint}")
    console.print(
        "[bold]Changes:[/bold] "
        f"+{statistics.added_count} ~{statistics.modified_count} "
        f"-{statistics.removed_count} moved:{statistics.renamed_count}"
    )
    if verbose and not summary:
        console.print(f"[bold]Generation:[/bold] {generation.generation_id}")
        console.print(
            f"[bold]Previous generation:[/bold] {generation.previous_generation_id or 'None'}"
        )
        console.print(f"[bold]Unchanged:[/bold] {statistics.unchanged_count}")
        console.print(
            f"[bold]Failed / skipped:[/bold] {statistics.failed_count} / {statistics.skipped_count}"
        )
    console.print(f"Reports: [green]{settings.reports_path}[/green]")


@app.command()
def graph(
    target: Annotated[
        str | None, typer.Argument(help="Workspace name, ID, or repository path.")
    ] = None,
    json_output: Annotated[bool, typer.Option("--json")] = False,
    summary: Annotated[bool, typer.Option("--summary")] = False,
    changes_only: Annotated[bool, typer.Option("--changes")] = False,
    orphans_only: Annotated[bool, typer.Option("--orphans")] = False,
    validate_only: Annotated[bool, typer.Option("--validate")] = False,
    verbose: Annotated[bool, typer.Option("--verbose")] = False,
) -> None:
    """Build or validate the structural engineering knowledge graph."""
    settings = _settings()
    logger = LoggingManager(settings.logs_path, settings.log_level).configure()
    workspace_manager = WorkspaceManager(
        JsonMemoryStore(settings.memory_path / "workspaces.json"), logger
    )
    workspace_id: str | None = None
    workspace_name: str | None = None
    try:
        if target is None:
            workspace = workspace_manager.current()
            root = workspace.repository_path if workspace else Path.cwd()
        else:
            try:
                workspace = workspace_manager.load(target)
                root = workspace.repository_path
            except WorkspaceNotFoundError:
                workspace = None
                candidate = Path(target).expanduser()
                if not candidate.exists():
                    console.print(
                        "[bold red]Graph target error:[/bold red] "
                        f"Workspace or repository path not found: {target}"
                    )
                    raise typer.Exit(code=2) from None
                root = candidate
        if workspace:
            workspace_id = workspace.workspace_id
            workspace_name = workspace.name
    except WorkspaceError as exc:
        console.print(f"[bold red]Graph target error:[/bold red] {exc}")
        raise typer.Exit(code=2) from exc

    graph_store = KnowledgeGraphRepository(settings.memory_path / "knowledge_graph.json")
    service = KnowledgeGraphService(
        settings.memory_path / "discovery.json",
        ProjectIndexStore(settings.memory_path / "index.json"),
        graph_store,
        settings.reports_path,
        logger,
        KnowledgeGraphConfiguration(
            max_nodes=settings.graph_max_nodes,
            max_edges=settings.graph_max_edges,
            max_module_depth=settings.graph_max_module_depth,
            include_directory_nodes=settings.graph_include_directory_nodes,
        ),
    )
    try:
        if validate_only:
            _, project_index, identity, _ = service.load_inputs(root, workspace_id)
            existing = graph_store.get(identity)
            if existing is None:
                raise KnowledgeGraphInputMissingError(
                    "Knowledge graph missing; run 'forge graph <target>' first"
                )
            validation = KnowledgeGraphValidator().validate(existing, project_index)
            console.print_json(validation.model_dump_json(indent=2))
            if not validation.valid:
                raise typer.Exit(code=7)
            return
        result = service.build(root, workspace_id, workspace_name)
    except KnowledgeGraphInputMissingError as exc:
        label = "index" if "index" in str(exc).casefold() else "discovery"
        code = 4 if label == "index" else 3
        console.print(f"[bold red]Graph input error:[/bold red] {exc}")
        raise typer.Exit(code=code) from exc
    except KnowledgeGraphInputMismatchError as exc:
        console.print(f"[bold red]Graph input mismatch:[/bold red] {exc}")
        raise typer.Exit(code=5) from exc
    except KnowledgeGraphValidationError as exc:
        console.print(f"[bold red]Graph validation failed:[/bold red] {exc}")
        raise typer.Exit(code=7) from exc
    except KnowledgeGraphPersistenceError as exc:
        console.print(f"[bold red]Graph persistence failed:[/bold red] {exc}")
        raise typer.Exit(code=8) from exc
    except KnowledgeGraphReportError as exc:
        console.print(f"[bold red]Graph reporting failed:[/bold red] {exc}")
        raise typer.Exit(code=9) from exc
    except KnowledgeGraphError as exc:
        console.print(f"[bold red]Graph build failed:[/bold red] {exc}")
        raise typer.Exit(code=6) from exc

    if changes_only:
        console.print_json(result.changes.model_dump_json(indent=2))
        return
    if orphans_only:
        console.print_json(result.orphans.model_dump_json(indent=2))
        return
    if json_output:
        console.print_json(result.model_dump_json(indent=2))
        return
    generation = result.graph.generation
    stats = generation.statistics
    console.print(f"[bold]Graph state:[/bold] {generation.graph_state_fingerprint}")
    console.print(f"[bold]Nodes / edges:[/bold] {stats.node_count} / {stats.edge_count}")
    console.print(
        f"[bold]Orphans / unassigned:[/bold] {stats.orphan_node_count} / "
        f"{stats.unassigned_file_count}"
    )
    if verbose and not summary:
        console.print(f"[bold]Generation:[/bold] {generation.generation_id}")
        console.print(f"[bold]Source index:[/bold] {generation.source_index_generation_id}")
        console.print(f"[bold]Node types:[/bold] {', '.join(stats.nodes_by_type)}")
        console.print(f"[bold]Edge types:[/bold] {', '.join(stats.edges_by_type)}")
    console.print(f"Reports: [green]{settings.reports_path}[/green]")


@app.command()
def capabilities(
    json_output: Annotated[bool, typer.Option("--json", help="Print registry JSON.")] = False,
    available: Annotated[
        bool, typer.Option("--available", help="Show available capabilities.")
    ] = False,
    planned: Annotated[bool, typer.Option("--planned", help="Show planned capabilities.")] = False,
    category: Annotated[str | None, typer.Option("--category", help="Filter by category.")] = None,
    project_type: Annotated[
        str | None, typer.Option("--project-type", help="Filter by project type.")
    ] = None,
    verbose: Annotated[
        bool, typer.Option("--verbose", help="Show contracts and limitations.")
    ] = False,
) -> None:
    """Build and list the canonical Forge capability registry."""
    settings = _settings()
    try:
        result = _capability_result(settings)
        query = CapabilityRegistryQuery(result.registry)
        values = query.list_capabilities()
        if available:
            values = tuple(x for x in values if query.is_available(x.capability_id))
        if planned:
            values = tuple(x for x in values if not query.is_available(x.capability_id))
        if category:
            try:
                selected = CapabilityCategory(category)
            except ValueError as exc:
                console.print(f"[bold red]Invalid capability category:[/bold red] {category}")
                raise typer.Exit(code=2) from exc
            values = tuple(x for x in values if x.category is selected)
        if project_type:
            values = tuple(x for x in values if project_type in x.supported_project_types)
    except CapabilityRegistryError as exc:
        console.print(f"[bold red]Capability registry failed:[/bold red] {exc}")
        raise typer.Exit(code=_capability_failure(exc)) from exc
    if json_output:
        payload = {
            "registry_id": result.registry.registry_id,
            "schema_version": result.registry.schema_version,
            "generation": result.registry.generation.model_dump(mode="json"),
            "statistics": result.registry.statistics.model_dump(mode="json"),
            "capabilities": [
                {
                    "definition": x.model_dump(mode="json"),
                    "evaluation": next(
                        e.model_dump(mode="json")
                        for e in result.registry.evaluations
                        if e.capability_id == x.capability_id
                    ),
                }
                for x in values
            ],
        }
        console.print_json(json.dumps(payload, sort_keys=True))
        return
    evaluations = {x.capability_id: x for x in result.registry.evaluations}
    table = Table(title="Forge Capabilities")
    for column in (
        "ID",
        "Name",
        "Status",
        "Implementation",
        "Maturity",
        "Milestone",
        "Access Mode",
    ):
        table.add_column(column)
    for item in values:
        evaluation = evaluations[item.capability_id]
        table.add_row(
            item.capability_id,
            item.display_name,
            evaluation.lifecycle.value,
            item.implementation_status.value,
            item.maturity.value,
            item.milestone,
            item.access_mode.value,
        )
        if verbose:
            table.add_row(
                "",
                "Requires: " + (", ".join(item.required_capabilities) or "none"),
                "Inputs: " + (", ".join(x.input_id for x in item.required_inputs) or "none"),
                "Outputs: " + (", ".join(x.output_id for x in item.produced_outputs) or "none"),
                "Commands: " + (", ".join(x.command for x in item.cli_commands) or "none"),
                "",
                "Reasons: " + (", ".join(evaluation.validation_messages) or "none"),
            )
    console.print(table)


@app.command()
def capability(
    capability_id: Annotated[str, typer.Argument(help="Canonical capability ID.")],
    json_output: Annotated[bool, typer.Option("--json", help="Print capability JSON.")] = False,
) -> None:
    """Show one canonical capability definition and evaluation."""
    settings = _settings()
    try:
        result = _capability_result(settings)
        query = CapabilityRegistryQuery(result.registry)
        definition = query.get_capability(capability_id)
        evaluation = next(
            x for x in result.registry.evaluations if x.capability_id == capability_id
        )
    except CapabilityNotFoundError as exc:
        console.print(f"[bold red]Unknown capability:[/bold red] {capability_id}")
        raise typer.Exit(code=2) from exc
    except CapabilityRegistryError as exc:
        console.print(f"[bold red]Capability registry failed:[/bold red] {exc}")
        raise typer.Exit(code=_capability_failure(exc)) from exc
    payload = {
        "definition": definition.model_dump(mode="json"),
        "evaluation": evaluation.model_dump(mode="json"),
    }
    if json_output:
        console.print_json(json.dumps(payload, sort_keys=True))
        return
    _print_capability_detail(definition, evaluation)


@app.command("show-memory")
def show_memory() -> None:
    """Print the persisted platform memory as JSON."""
    settings = _settings()
    memory = JsonMemoryStore(settings.memory_path / "knowledge.json")
    console.print_json(json.dumps(memory.read(), default=str))


@app.command()
def version() -> None:
    """Print the installed platform version."""
    console.print(__version__)
