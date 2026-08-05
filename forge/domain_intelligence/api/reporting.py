"""Reporting for M4.4 API Domain Intelligence."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from forge.domain_intelligence.api.errors import (
    ApiIntelligenceError,
)
from forge.domain_intelligence.api.models import (
    ApiAnalysisReport,
)


def api_report_summary(
    report: ApiAnalysisReport,
) -> dict[str, object]:
    """Return a deterministic API summary."""
    categories = Counter(
        finding.category for finding in report.findings
    )

    endpoint_count = sum(
        len(contract.endpoints)
        for contract in report.contracts
    )

    authenticated_endpoint_count = sum(
        1
        for contract in report.contracts
        for endpoint in contract.endpoints
        if endpoint.authentication
    )

    return {
        "report_id": report.report_id,
        "project_id": report.project.project_id,
        "project_root": report.project.root,
        "styles": [
            style.value for style in report.project.styles
        ],
        "contract_file_count": len(
            report.project.contract_files
        ),
        "source_file_count": len(
            report.project.source_files
        ),
        "configuration_file_count": len(
            report.project.configuration_files
        ),
        "contract_count": len(report.contracts),
        "endpoint_count": endpoint_count,
        "authenticated_endpoint_count": (
            authenticated_endpoint_count
        ),
        "finding_count": len(report.findings),
        "finding_categories": dict(
            sorted(categories.items())
        ),
    }


def render_api_markdown(
    report: ApiAnalysisReport,
) -> str:
    """Render a stable Markdown API-intelligence report."""
    summary = api_report_summary(report)

    lines = [
        "# API Intelligence Report",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Project ID: `{report.project.project_id}`",
        f"- Project root: `{report.project.root}`",
        (
            "- Styles: "
            + ", ".join(
                style.value
                for style in report.project.styles
            )
        ),
        f"- Contracts: `{summary['contract_count']}`",
        f"- Endpoints: `{summary['endpoint_count']}`",
        (
            "- Authenticated endpoints: "
            f"`{summary['authenticated_endpoint_count']}`"
        ),
        f"- Findings: `{summary['finding_count']}`",
        "",
        "## API Artifacts",
        "",
        (
            "- Contract files: "
            + (
                ", ".join(report.project.contract_files)
                if report.project.contract_files
                else "none detected"
            )
        ),
        (
            "- Source files: "
            + (
                ", ".join(report.project.source_files)
                if report.project.source_files
                else "none detected"
            )
        ),
        (
            "- Configuration files: "
            + (
                ", ".join(
                    report.project.configuration_files
                )
                if report.project.configuration_files
                else "none detected"
            )
        ),
        "",
        "## Contracts",
        "",
    ]

    if not report.contracts:
        lines.append("No API contracts were detected.")
        lines.append("")
    else:
        for contract in report.contracts:
            lines.extend(
                [
                    f"### {contract.title}",
                    "",
                    f"- Contract ID: `{contract.contract_id}`",
                    f"- Style: `{contract.style.value}`",
                    (
                        f"- Version: `{contract.version}`"
                        if contract.version is not None
                        else "- Version: not declared"
                    ),
                    f"- Source: `{contract.source_path}`",
                    (
                        "- Endpoints: "
                        f"`{len(contract.endpoints)}`"
                    ),
                    "",
                ]
            )

            if contract.endpoints:
                lines.append(
                    "| Method | Path | Operation | Auth |"
                )
                lines.append("|---|---|---|---|")

                for endpoint in contract.endpoints:
                    auth = (
                        ", ".join(
                            item.value
                            for item in endpoint.authentication
                        )
                        if endpoint.authentication
                        else "none detected"
                    )
                    lines.append(
                        "| "
                        f"{endpoint.method.value} | "
                        f"{endpoint.path} | "
                        f"{endpoint.operation_id or ''} | "
                        f"{auth} |"
                    )

                lines.append("")

    lines.extend(
        [
            "## Findings",
            "",
        ]
    )

    if not report.findings:
        lines.append("No API findings were produced.")
    else:
        for finding in report.findings:
            lines.extend(
                [
                    f"### {finding.category}",
                    "",
                    f"- Finding ID: `{finding.finding_id}`",
                    f"- Severity: `{finding.severity.value}`",
                    f"- Message: {finding.message}",
                    (
                        f"- Path: `{finding.path}`"
                        if finding.path is not None
                        else "- Path: not applicable"
                    ),
                ]
            )

            if finding.evidence:
                lines.append("- Evidence:")
                for key, value in sorted(
                    finding.evidence.items()
                ):
                    lines.append(
                        f"  - `{key}`: `{value}`"
                    )

            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_api_report_bundle(
    report: ApiAnalysisReport,
    destination: Path,
) -> dict[str, Path]:
    """Write JSON, summary JSON, and Markdown reports."""
    try:
        destination.mkdir(parents=True, exist_ok=True)

        raw_json = destination / "API_ANALYSIS.json"
        summary_json = destination / "API_SUMMARY.json"
        markdown = destination / "API_ANALYSIS.md"

        raw_json.write_text(
            json.dumps(
                report.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        summary_json.write_text(
            json.dumps(
                api_report_summary(report),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        markdown.write_text(
            render_api_markdown(report),
            encoding="utf-8",
        )
    except OSError as exc:
        raise ApiIntelligenceError(
            f"unable to write API report bundle: {destination}"
        ) from exc

    return {
        raw_json.name: raw_json,
        summary_json.name: summary_json,
        markdown.name: markdown,
    }