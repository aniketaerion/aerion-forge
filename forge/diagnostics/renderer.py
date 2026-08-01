"""Deterministic portable diagnostic report rendering."""

import json
from pathlib import Path

from forge.diagnostics.errors import DiagnosticReportError
from forge.diagnostics.models import DiagnosticSnapshot


class DiagnosticRenderer:
    def render(self, snapshot: DiagnosticSnapshot, runtime: bool) -> dict[str, str]:
        payload = snapshot.model_dump(mode="json")
        summary = snapshot.summary.model_dump(mode="json")
        actions = {
            item.check_id: [action.model_dump(mode="json") for action in item.corrective_actions]
            for item in snapshot.results
            if item.corrective_actions
        }
        changes = snapshot.changes.model_dump(mode="json")
        title = "Forge Runtime Health" if runtime else "Forge Target Diagnostics"
        markdown = "\n".join(
            (
                f"# {title}",
                "",
                f"Overall status: **{snapshot.summary.overall_status.value.upper()}**",
                "",
                f"- Total checks: {snapshot.summary.total_checks}",
                f"- Healthy: {snapshot.summary.healthy_count}",
                f"- Degraded: {snapshot.summary.degraded_count}",
                f"- Unhealthy: {snapshot.summary.unhealthy_count}",
                f"- Unknown: {snapshot.summary.unknown_count}",
                f"- Blocking: {snapshot.summary.blocking_count}",
                "",
                "## Non-healthy checks",
                "",
                *(
                    f"- `{item.check_id}`: {item.status.value} — {item.summary}"
                    for item in snapshot.results
                    if item.status.value not in {"healthy", "not_applicable"}
                ),
            )
        )
        reports = {
            "DIAGNOSTIC_RESULTS.json": json.dumps(payload, indent=2, sort_keys=True) + "\n",
            "DIAGNOSTIC_SUMMARY.json": json.dumps(summary, indent=2, sort_keys=True) + "\n",
            "DIAGNOSTIC_SUMMARY.md": markdown.rstrip() + "\n",
            "DIAGNOSTIC_ACTIONS.json": json.dumps(actions, indent=2, sort_keys=True) + "\n",
            "DIAGNOSTIC_CHANGES.json": json.dumps(changes, indent=2, sort_keys=True) + "\n",
        }
        if runtime:
            reports["RUNTIME_HEALTH.json"] = reports["DIAGNOSTIC_RESULTS.json"]
            reports["RUNTIME_HEALTH_SUMMARY.md"] = markdown.rstrip() + "\n"
        return dict(sorted(reports.items()))

    def write(self, reports_path: Path, snapshot: DiagnosticSnapshot, runtime: bool) -> None:
        reports_path.mkdir(parents=True, exist_ok=True)
        staged: list[tuple[Path, Path]] = []
        try:
            for name, content in self.render(snapshot, runtime).items():
                destination = (reports_path / name).resolve()
                if reports_path.resolve() not in destination.parents:
                    raise DiagnosticReportError("Diagnostic report path escapes output directory.")
                temporary = destination.with_suffix(destination.suffix + ".tmp")
                temporary.write_text(content, encoding="utf-8", newline="\n")
                staged.append((temporary, destination))
            for temporary, destination in staged:
                temporary.replace(destination)
        except (OSError, DiagnosticReportError) as exc:
            for temporary, _ in staged:
                temporary.unlink(missing_ok=True)
            if isinstance(exc, DiagnosticReportError):
                raise
            raise DiagnosticReportError("Unable to write diagnostic reports.") from exc
