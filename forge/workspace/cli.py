"""Workspace command group for the Forge CLI."""

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from forge.config import Settings
from forge.core import LoggingManager
from forge.memory import JsonMemoryStore
from forge.workspace.errors import WorkspaceError
from forge.workspace.manager import WorkspaceManager
from forge.workspace.models import ProjectType, Workspace

workspace_app = typer.Typer(help="Register, select, inspect, and diagnose software projects.")
console = Console()


def _manager() -> WorkspaceManager:
    settings = Settings()
    settings.ensure_runtime_directories()
    logger = LoggingManager(settings.logs_path, settings.log_level).configure()
    return WorkspaceManager(JsonMemoryStore(settings.memory_path / "workspaces.json"), logger)


def _fail(exc: WorkspaceError) -> None:
    console.print(f"[bold red]Workspace error:[/bold red] {exc}")
    raise typer.Exit(code=1) from exc


def _workspace_json(workspace: Workspace) -> str:
    return json.dumps(workspace.model_dump(mode="json"), indent=2)


def _render_list(workspaces: list[Workspace]) -> None:
    table = Table(title="Forge Workspaces")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Repository")
    table.add_column("Status")
    table.add_column("Health")
    for workspace in workspaces:
        table.add_row(
            workspace.name,
            workspace.project_type.value,
            str(workspace.repository_path),
            workspace.status.value,
            workspace.health.value,
        )
    console.print(table)


@workspace_app.command("add")
def add_workspace(
    name: Annotated[str, typer.Argument(help="Unique workspace name.")],
    repository: Annotated[Path, typer.Argument(help="Repository directory.")],
    project_type: Annotated[
        ProjectType, typer.Option("--type", help="Project category.")
    ] = ProjectType.GENERIC,
    description: Annotated[str, typer.Option("--description")] = "",
    tag: Annotated[list[str] | None, typer.Option("--tag", help="Repeatable metadata tag.")] = None,
) -> None:
    """Register a repository as a workspace."""
    try:
        workspace = _manager().register(name, repository, project_type, description, tag)
    except WorkspaceError as exc:
        _fail(exc)
    console.print(f"Workspace created: [green]{workspace.name}[/green]")


@workspace_app.command("remove")
def remove_workspace(
    reference: Annotated[str, typer.Argument(help="Workspace name or ID.")],
) -> None:
    """Remove a workspace registration without deleting repository files."""
    try:
        workspace = _manager().delete(reference)
    except WorkspaceError as exc:
        _fail(exc)
    console.print(f"Workspace removed: [green]{workspace.name}[/green]")


@workspace_app.command("rename")
def rename_workspace(
    reference: Annotated[str, typer.Argument(help="Workspace name or ID.")],
    new_name: Annotated[str, typer.Argument(help="New unique name.")],
) -> None:
    """Rename a registered workspace."""
    try:
        workspace = _manager().rename(reference, new_name)
    except WorkspaceError as exc:
        _fail(exc)
    console.print(f"Workspace renamed: [green]{workspace.name}[/green]")


@workspace_app.command("update")
def update_workspace(
    reference: Annotated[str, typer.Argument(help="Workspace name or ID.")],
    repository: Annotated[Path | None, typer.Option("--repository")] = None,
    project_type: Annotated[ProjectType | None, typer.Option("--type")] = None,
    description: Annotated[str | None, typer.Option("--description")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    notes: Annotated[str | None, typer.Option("--notes")] = None,
) -> None:
    """Update editable workspace metadata."""
    changes: dict[str, Any] = {
        "repository_path": repository,
        "project_type": project_type,
        "description": description,
        "tags": tag,
        "notes": notes,
    }
    try:
        workspace = _manager().update(reference, **changes)
    except WorkspaceError as exc:
        _fail(exc)
    console.print(f"Workspace updated: [green]{workspace.name}[/green]")


@workspace_app.command("list")
def list_workspaces() -> None:
    """List all registered workspaces."""
    try:
        _render_list(_manager().list())
    except WorkspaceError as exc:
        _fail(exc)


@workspace_app.command("search")
def search_workspaces(
    query: Annotated[str, typer.Argument(help="Case-insensitive query.")],
) -> None:
    """Search workspace metadata."""
    try:
        _render_list(_manager().search(query))
    except WorkspaceError as exc:
        _fail(exc)


@workspace_app.command("use")
def use_workspace(reference: Annotated[str, typer.Argument(help="Workspace name or ID.")]) -> None:
    """Select the active workspace."""
    try:
        workspace = _manager().select(reference)
    except WorkspaceError as exc:
        _fail(exc)
    console.print(f"Active workspace: [green]{workspace.name}[/green]")


@workspace_app.command("show")
def show_workspace(reference: Annotated[str, typer.Argument(help="Workspace name or ID.")]) -> None:
    """Show complete workspace metadata as JSON."""
    try:
        workspace = _manager().load(reference)
    except WorkspaceError as exc:
        _fail(exc)
    console.print_json(_workspace_json(workspace))


@workspace_app.command("current")
def current_workspace() -> None:
    """Show the active workspace."""
    try:
        workspace = _manager().current()
    except WorkspaceError as exc:
        _fail(exc)
    if workspace is None:
        console.print("No active workspace.")
        return
    console.print_json(_workspace_json(workspace))


@workspace_app.command("validate")
def validate_workspace(
    reference: Annotated[str, typer.Argument(help="Workspace name or ID.")],
) -> None:
    """Validate a workspace and refresh detected metadata."""
    try:
        workspace = _manager().validate(reference)
    except WorkspaceError as exc:
        _fail(exc)
    console.print(
        f"Workspace validation: [green]{workspace.name}[/green] "
        f"({workspace.status.value}, {workspace.health.value})"
    )


@workspace_app.command("doctor")
def doctor_workspace(
    reference: Annotated[str, typer.Argument(help="Workspace name or ID.")],
) -> None:
    """Run workspace environment diagnostics."""
    try:
        diagnostics = _manager().doctor(reference)
    except WorkspaceError as exc:
        _fail(exc)
    table = Table(title="Workspace Doctor")
    table.add_column("Check")
    table.add_column("Available")
    table.add_column("Detail")
    for check in diagnostics.checks:
        table.add_row(check.name, "yes" if check.available else "no", check.detail)
    table.add_row(
        "Missing Dependencies",
        "no" if diagnostics.missing_dependencies else "yes",
        ", ".join(diagnostics.missing_dependencies) or "none",
    )
    table.add_row("Workspace Health", "", diagnostics.workspace_health.value)
    table.add_row("Overall Status", "", diagnostics.overall_status.value)
    console.print(table)
