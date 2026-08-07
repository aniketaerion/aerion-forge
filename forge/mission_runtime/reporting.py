"""Mission runtime reporting."""

from __future__ import annotations

from dataclasses import dataclass

from forge.mission_runtime.models import MissionSession


@dataclass(frozen=True, slots=True)
class MissionRuntimeReport:
    session_id: str
    state: str
    repository_root: str
    selected_capabilities: tuple[str, ...]
    execution_run_ids: tuple[str, ...]
    verification_references: tuple[str, ...]
    review_package_reference: str | None
    failure_reason: str | None


def build_mission_report(
    session: MissionSession,
) -> MissionRuntimeReport:
    return MissionRuntimeReport(
        session_id=session.session_id,
        state=session.state.value,
        repository_root=session.repository_root,
        selected_capabilities=session.selected_capabilities,
        execution_run_ids=session.execution_run_ids,
        verification_references=session.verification_references,
        review_package_reference=session.review_package_reference,
        failure_reason=session.failure_reason,
    )