"""Deterministic Execution Controller report rendering."""

import json
from collections.abc import Mapping
from pathlib import Path

from forge.execution_controller.errors import (
    ExecutionReportError,
)
from forge.execution_controller.models import (
    ExecutionEvidence,
    ExecutionOperation,
    ExecutionSession,
    ExecutionTransition,
)


class ExecutionControllerRenderer:
    """Render canonical Execution Controller report artifacts."""

    REPORT_NAME = "EXECUTION_CONTROLLER.json"
    SUMMARY_NAME = "EXECUTION_CONTROLLER_SUMMARY.json"
    EVIDENCE_NAME = "EXECUTION_CONTROLLER_EVIDENCE.json"
    TRANSITIONS_NAME = "EXECUTION_CONTROLLER_TRANSITIONS.json"
    MARKDOWN_NAME = "EXECUTION_CONTROLLER.md"

    def render_json(
        self,
        session: ExecutionSession,
    ) -> str:
        return self._json(session.model_dump(mode="json"))

    def render_summary_json(
        self,
        session: ExecutionSession,
    ) -> str:
        payload = {
            "schema_version": session.schema_version,
            "session_id": session.session_id,
            "session_fingerprint": (session.session_fingerprint),
            "request_id": session.request.request_id,
            "request_fingerprint": (session.request.request_fingerprint),
            "mission_id": session.request.mission_id,
            "current_state": session.current_state.value,
            "dry_run": session.request.dry_run,
            "approval_id": (session.approval.approval_id if session.approval is not None else None),
            "statistics": session.statistics.model_dump(mode="json"),
            "transition_count": len(session.transitions),
            "evidence_count": len(session.evidence),
            "source_fingerprints": dict(session.source_fingerprints),
        }

        return self._json(payload)

    def render_evidence_json(
        self,
        session: ExecutionSession,
    ) -> str:
        payload = {
            "schema_version": session.schema_version,
            "session_id": session.session_id,
            "session_fingerprint": (session.session_fingerprint),
            "evidence": [self._evidence_payload(item) for item in session.evidence],
        }

        return self._json(payload)

    def render_transitions_json(
        self,
        session: ExecutionSession,
    ) -> str:
        payload = {
            "schema_version": session.schema_version,
            "session_id": session.session_id,
            "session_fingerprint": (session.session_fingerprint),
            "current_state": session.current_state.value,
            "transitions": [self._transition_payload(item) for item in session.transitions],
        }

        return self._json(payload)

    def render_markdown(
        self,
        session: ExecutionSession,
    ) -> str:
        lines = [
            "# Execution Controller Report",
            "",
            f"- Session ID: `{session.session_id}`",
            f"- Mission ID: `{session.request.mission_id}`",
            f"- Request ID: `{session.request.request_id}`",
            f"- State: `{session.current_state.value}`",
            f"- Dry run: `{str(session.request.dry_run).lower()}`",
            (
                "- Approval ID: "
                + (
                    f"`{session.approval.approval_id}`"
                    if session.approval is not None
                    else "`none`"
                )
            ),
            (f"- Session fingerprint: `{session.session_fingerprint}`"),
            "",
            "## Statistics",
            "",
            (f"- Operations: {session.statistics.operation_count}"),
            (f"- Pending: {session.statistics.pending_count}"),
            (f"- Running: {session.statistics.running_count}"),
            (f"- Succeeded: {session.statistics.succeeded_count}"),
            (f"- Failed: {session.statistics.failed_count}"),
            (f"- Blocked: {session.statistics.blocked_count}"),
            (f"- Cancelled: {session.statistics.cancelled_count}"),
            "",
            "## Operations",
            "",
        ]

        if session.operations:
            lines.extend(self._operation_markdown(operation) for operation in session.operations)
        else:
            lines.append("- None")

        lines.extend(
            [
                "",
                "## State transitions",
                "",
            ]
        )

        if session.transitions:
            lines.extend(
                self._transition_markdown(transition) for transition in session.transitions
            )
        else:
            lines.append("- None")

        lines.extend(
            [
                "",
                "## Evidence",
                "",
            ]
        )

        if session.evidence:
            lines.extend(self._evidence_markdown(evidence) for evidence in session.evidence)
        else:
            lines.append("- None")

        lines.extend(
            [
                "",
                "## Source fingerprints",
                "",
            ]
        )

        if session.source_fingerprints:
            lines.extend(
                (f"- `{key}`: `{session.source_fingerprints[key]}`")
                for key in sorted(session.source_fingerprints)
            )
        else:
            lines.append("- None")

        return "\n".join(lines).rstrip() + "\n"

    def render_suite(
        self,
        session: ExecutionSession,
    ) -> Mapping[str, str]:
        return {
            self.REPORT_NAME: self.render_json(session),
            self.SUMMARY_NAME: (self.render_summary_json(session)),
            self.EVIDENCE_NAME: (self.render_evidence_json(session)),
            self.TRANSITIONS_NAME: (self.render_transitions_json(session)),
            self.MARKDOWN_NAME: (self.render_markdown(session)),
        }

    def write_suite(
        self,
        session: ExecutionSession,
        reports_path: Path,
    ) -> tuple[str, ...]:
        reports_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        suite = self.render_suite(session)
        written: list[Path] = []
        backups: dict[Path, bytes] = {}

        try:
            for name, content in suite.items():
                destination = reports_path / name

                if destination.exists():
                    backups[destination] = destination.read_bytes()

                temporary = destination.with_name(destination.name + ".tmp")

                temporary.write_text(
                    content,
                    encoding="utf-8",
                    newline="\n",
                )
                temporary.replace(destination)
                written.append(destination)

        except OSError as exc:
            self._restore_reports(
                written,
                backups,
            )
            self._remove_temporary_files(
                reports_path,
                suite,
            )

            raise ExecutionReportError(
                "Unable to write the complete Execution Controller report suite."
            ) from exc

        self._remove_temporary_files(
            reports_path,
            suite,
        )

        return tuple(path.as_posix() for path in sorted(written))

    def _json(
        self,
        payload: object,
    ) -> str:
        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )

    def _operation_markdown(
        self,
        operation: ExecutionOperation,
    ) -> str:
        return (
            f"- `{operation.operation_id}` — "
            f"task `{operation.task_id}`, "
            f"tool `{operation.tool_id}`, "
            f"type `{operation.operation_type}`, "
            f"status `{operation.status.value}`"
        )

    def _transition_markdown(
        self,
        transition: ExecutionTransition,
    ) -> str:
        return (
            f"- `{transition.transition_id}` — "
            f"`{transition.previous_state.value}` "
            f"→ `{transition.next_state.value}` "
            f"via `{transition.event.value}`"
        )

    def _evidence_markdown(
        self,
        evidence: ExecutionEvidence,
    ) -> str:
        return (
            f"- `{evidence.evidence_id}` — "
            f"type `{evidence.evidence_type.value}`, "
            f"source `{evidence.source}`, "
            f"reference `{evidence.reference}`"
        )

    def _transition_payload(
        self,
        transition: ExecutionTransition,
    ) -> dict[str, object]:
        return transition.model_dump(mode="json")

    def _evidence_payload(
        self,
        evidence: ExecutionEvidence,
    ) -> dict[str, object]:
        return evidence.model_dump(mode="json")

    def _restore_reports(
        self,
        written: list[Path],
        backups: Mapping[Path, bytes],
    ) -> None:
        for destination in reversed(written):
            try:
                if destination in backups:
                    destination.write_bytes(backups[destination])
                elif destination.exists():
                    destination.unlink()
            except OSError:
                continue

    def _remove_temporary_files(
        self,
        reports_path: Path,
        suite: Mapping[str, str],
    ) -> None:
        for name in suite:
            temporary = reports_path / (name + ".tmp")

            try:
                if temporary.exists():
                    temporary.unlink()
            except OSError:
                continue
