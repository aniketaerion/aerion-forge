from pathlib import Path

from typer.testing import CliRunner

from forge.domain_intelligence.knowledge_loader.cli import (
    knowledge_loader_app,
)

runner = CliRunner()


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def initialize_knowledge_project(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "# Forge Guide\nKnowledge loading.",
        encoding="utf-8",
    )


def test_knowledge_loader_load_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_knowledge_project(tmp_path)

    result = runner.invoke(
        knowledge_loader_app,
        [
            "load",
            "--repository-root",
            str(tmp_path),
            "--project-root",
            "docs",
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Knowledge Loader Intelligence" in normalized
    assert "Sources" in normalized


def test_knowledge_loader_summary_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_knowledge_project(tmp_path)

    result = runner.invoke(
        knowledge_loader_app,
        [
            "summary",
            "--repository-root",
            str(tmp_path),
            "--project-root",
            "docs",
        ],
    )

    assert result.exit_code == 0
    assert '"source_count"' in result.stdout
    assert '"chunk_count"' in result.stdout


def test_knowledge_loader_report_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_knowledge_project(tmp_path)

    result = runner.invoke(
        knowledge_loader_app,
        [
            "report",
            "--repository-root",
            str(tmp_path),
            "--project-root",
            "docs",
            "--destination",
            "reports/knowledge-loader",
        ],
    )

    assert result.exit_code == 0
    report_root = (
        tmp_path / "reports" / "knowledge-loader"
    )
    assert (
        report_root / "KNOWLEDGE_LOAD_REPORT.json"
    ).is_file()
    assert (
        report_root / "KNOWLEDGE_LOAD_SUMMARY.json"
    ).is_file()
    assert (
        report_root / "KNOWLEDGE_LOAD_REPORT.md"
    ).is_file()


def test_knowledge_loader_validate_command(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    initialize_knowledge_project(tmp_path)

    result = runner.invoke(
        knowledge_loader_app,
        [
            "validate",
            "--repository-root",
            str(tmp_path),
            "--project-root",
            "docs",
        ],
    )

    assert result.exit_code == 0
    assert "validation passed" in result.stdout.lower()