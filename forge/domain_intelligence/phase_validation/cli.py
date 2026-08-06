"""CLI for M4.8 Phase Validation Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationRequest,
)
from forge.domain_intelligence.phase_validation.reporting import (
    phase_validation_report_summary,
    write_phase_validation_report_bundle,
)
from forge.domain_intelligence.phase_validation.service import (
    PhaseValidationService,
)

phase_validation_app = typer.Typer(
    help=(
        "Validate architecture, acceptance criteria, coverage, "
        "compatibility, release readiness, and phase completion."
    ),
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    phase: str,
    milestone: str | None,
    require_clean_worktree: bool,
    require_release_tag: bool,
    minimum_test_count: int,
    minimum_coverage_percent: float,
) -> PhaseValidationRequest:
    return PhaseValidationRequest(
        repository_root=str(repository_root.resolve()),
        phase=phase,
        milestone=milestone,
        require_clean_worktree=require_clean_worktree,
        require_release_tag=require_release_tag,
        minimum_test_count=minimum_test_count,
        minimum_coverage_percent=minimum_coverage_percent,
    )


@phase_validation_app.command("validate")
def validate_phase(
    repository_root: Annotated[
        Path,
        typer.Option(
            "--repository-root",
            help="Git repository root.",
        ),
    ] = Path("."),
    phase: Annotated[
        str,
        typer.Option(
            "--phase",
            help="Phase identifier, for example 4.",
        ),
    ] = "4",
    milestone: Annotated[
        str | None,
        typer.Option(
            "--milestone",
            help="Optional milestone identifier, for example M4.8.",
        ),
    ] = None,
    require_clean_worktree: Annotated[
        bool,
        typer.Option(
            "--require-clean-worktree/--allow-dirty-worktree",
            help="Require a clean Git working tree.",
        ),
    ] = True,
    require_release_tag: Annotated[
        bool,
        typer.Option(
            "--require-release-tag/--allow-missing-release-tag",
            help="Require a release tag.",
        ),
    ] = False,
    minimum_test_count: Annotated[
        int,
        typer.Option(
            "--minimum-test-count",
            min=0,
            help="Minimum collected test count.",
        ),
    ] = 1,
    minimum_coverage_percent: Annotated[
        float,
        typer.Option(
            "--minimum-coverage-percent",
            min=0.0,
            max=100.0,
            help="Minimum required code coverage percentage.",
        ),
    ] = 0.0,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the complete JSON report.",
        ),
    ] = False,
) -> None:
    """Run phase-validation intelligence."""
    report = PhaseValidationService().validate(
        _request(
            repository_root,
            phase,
            milestone,
            require_clean_worktree,
            require_release_tag,
            minimum_test_count,
            minimum_coverage_percent,
        )
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = phase_validation_report_summary(report)

    table = Table(title="Phase Validation Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Phase", str(summary["phase"]))
    table.add_row(
        "Milestone",
        str(summary["milestone"] or "-"),
    )
    table.add_row(
        "Result",
        "PASS" if summary["passed"] else "FAIL",
    )
    table.add_row("Checks", str(summary["check_count"]))
    table.add_row("Results", str(summary["result_count"]))
    table.add_row("Findings", str(summary["finding_count"]))
    table.add_row(
        "Required passed",
        (
            f"{summary['passed_required_check_count']}/"
            f"{summary['required_check_count']}"
        ),
    )

    console.print(table)


@phase_validation_app.command("summary")
def summarize_phase(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    phase: Annotated[
        str,
        typer.Option("--phase"),
    ] = "4",
    milestone: Annotated[
        str | None,
        typer.Option("--milestone"),
    ] = None,
) -> None:
    """Print a concise phase-validation summary."""
    report = PhaseValidationService().validate(
        _request(
            repository_root,
            phase,
            milestone,
            True,
            False,
            1,
            0.0,
        )
    )

    console.print_json(
        json.dumps(
            phase_validation_report_summary(report),
            sort_keys=True,
        )
    )


@phase_validation_app.command("report")
def report_phase(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    phase: Annotated[
        str,
        typer.Option("--phase"),
    ] = "4",
    milestone: Annotated[
        str | None,
        typer.Option("--milestone"),
    ] = None,
    destination: Annotated[
        Path,
        typer.Option(
            "--destination",
            help="Repository-relative report destination.",
        ),
    ] = Path("reports/latest/phase-validation"),
) -> None:
    """Generate phase-validation JSON and Markdown reports."""
    root = repository_root.resolve()
    report = PhaseValidationService().validate(
        _request(
            root,
            phase,
            milestone,
            True,
            False,
            1,
            0.0,
        )
    )
    written = write_phase_validation_report_bundle(
        report,
        root / destination,
    )

    console.print_json(
        json.dumps(
            {
                name: str(path)
                for name, path in sorted(written.items())
            },
            sort_keys=True,
        )
    )