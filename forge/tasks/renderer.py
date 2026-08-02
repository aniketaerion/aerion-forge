"""Deterministic JSON and Markdown reports for Task Management."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from forge.tasks.errors import TaskReportError
from forge.tasks.models import (
    TaskChangeSet,
    TaskGeneration,
    TaskSet,
)


class TaskRenderer:
    """Build and atomically write deterministic task reports."""

    REPORT_NAMES = (
        "TASK_PLAN.json",
        "TASK_SUMMARY.json",
        "TASK_CHANGES.json",
        "TASK_PLAN.md",
        "TASK_SUMMARY.md",
    )

    def render(
        self,
        task_set: TaskSet,
        generation: TaskGeneration,
        changes: TaskChangeSet,
    ) -> dict[str, str]:
        """Render the canonical Task Management report suite."""

        plan_payload = task_set.model_dump(
            mode="json",
            exclude_none=False,
        )

        summary_payload: dict[str, Any] = {
            "schema_version": task_set.schema_version,
            "mission_id": task_set.mission_id,
            "mission_fingerprint": task_set.mission_fingerprint,
            "task_set_fingerprint": task_set.task_set_fingerprint,
            "generation_id": generation.generation_id,
            "task_count": len(task_set.tasks),
            "statistics": task_set.statistics.model_dump(
                mode="json",
                exclude_none=False,
            ),
        }

        changes_payload = changes.model_dump(
            mode="json",
            exclude_none=False,
        )

        return {
            "TASK_PLAN.json": self._json(plan_payload),
            "TASK_SUMMARY.json": self._json(summary_payload),
            "TASK_CHANGES.json": self._json(changes_payload),
            "TASK_PLAN.md": self._markdown(
                task_set,
                generation,
                summary=False,
            ),
            "TASK_SUMMARY.md": self._markdown(
                task_set,
                generation,
                summary=True,
            ),
        }

    def write(
        self,
        directory: Path,
        reports: dict[str, str],
    ) -> tuple[str, ...]:
        """Write the canonical report suite atomically."""

        expected = set(self.REPORT_NAMES)
        actual = set(reports)

        if actual != expected:
            missing = sorted(expected - actual)
            unexpected = sorted(actual - expected)

            raise TaskReportError(
                "Task report set is invalid. "
                f"Missing={missing}; unexpected={unexpected}."
            )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        written: list[str] = []

        try:
            for name in self.REPORT_NAMES:
                self._atomic_write(
                    directory / name,
                    reports[name].encode("utf-8"),
                )
                written.append(name)
        except TaskReportError:
            raise
        except Exception as exc:
            raise TaskReportError(
                "Task report generation failed."
            ) from exc

        return tuple(written)

    def _json(self, payload: Any) -> str:
        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )

    def _markdown(
        self,
        task_set: TaskSet,
        generation: TaskGeneration,
        *,
        summary: bool,
    ) -> str:
        lines = [
            "# Task Management Summary"
            if summary
            else "# Task Management Plan",
            "",
            f"- Mission ID: `{task_set.mission_id}`",
            f"- Generation ID: `{generation.generation_id}`",
            f"- Task-set fingerprint: `{task_set.task_set_fingerprint}`",
            f"- Total tasks: {task_set.statistics.total_tasks}",
            f"- Draft: {task_set.statistics.draft_tasks}",
            f"- Ready: {task_set.statistics.ready_tasks}",
            f"- Blocked: {task_set.statistics.blocked_tasks}",
            f"- In progress: {task_set.statistics.in_progress_tasks}",
            f"- Review: {task_set.statistics.review_tasks}",
            f"- Validated: {task_set.statistics.validated_tasks}",
            f"- Completed: {task_set.statistics.completed_tasks}",
            "",
        ]

        if summary:
            return "\n".join(lines).rstrip() + "\n"

        lines.extend(
            [
                "## Tasks",
                "",
            ]
        )

        for task in task_set.tasks:
            lines.extend(
                [
                    f"### {task.sequence}. {task.title}",
                    "",
                    f"- Task ID: `{task.task_id}`",
                    f"- Workstream: `{task.workstream_id}`",
                    f"- Status: `{task.status.value}`",
                    f"- Priority: `{task.priority.value}`",
                    f"- Risk: `{task.risk_level.value}`",
                    (
                        f"- Parent: `{task.parent_task_id}`"
                        if task.parent_task_id is not None
                        else "- Parent: none"
                    ),
                    "",
                    task.description,
                    "",
                    "Acceptance criteria:",
                    "",
                ]
            )

            lines.extend(
                f"- {criterion.statement}"
                for criterion in task.acceptance_criteria
            )

            lines.extend(
                [
                    "",
                    "Validation requirements:",
                    "",
                ]
            )

            lines.extend(
                (
                    f"- [{requirement.category.value}] "
                    f"{requirement.description}"
                )
                for requirement in task.validation_requirements
            )

            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def _atomic_write(
        self,
        path: Path,
        content: bytes,
    ) -> None:
        temporary: Path | None = None

        try:
            descriptor, name = tempfile.mkstemp(
                prefix=f".{path.name}.",
                suffix=".tmp",
                dir=path.parent,
            )
            temporary = Path(name)

            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(temporary, path)
            temporary = None
        except OSError as exc:
            raise TaskReportError(
                f"Unable to write task report: {path.name}"
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
