"""CLI for the M5.8 Forge Mission Runtime."""

from __future__ import annotations

import typer

app = typer.Typer(
    name="mission-runtime",
    help="Inspect M5.8 Forge Mission Runtime capabilities.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Forge Mission Runtime command group."""


@app.command("about")
def about() -> None:
    """Describe the mission runtime integration boundary."""
    typer.echo(
        "M5.8 Forge Mission Runtime: context -> memory -> planning -> "
        "approval -> execution -> verification -> review."
    )