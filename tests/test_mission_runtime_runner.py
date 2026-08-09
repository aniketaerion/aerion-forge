from pathlib import Path

from forge.agent_runtime.models import AgentSessionStatus
from forge.mission_runtime.runner import (
    approve_plan,
    load_session,
    run_objective,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_runner_stops_at_plan_approval(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = run_objective(
        objective="Plan calculator change",
        repository_root=tmp_path,
    )

    assert result.session.status is AgentSessionStatus.AWAITING_APPROVAL

    persisted = load_session(
        session_id=result.session_id,
        repository_root=tmp_path,
    )
    assert persisted.session_id == result.session_id


def test_runner_resumes_after_plan_approval(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    created = run_objective(
        objective="Plan calculator change",
        repository_root=tmp_path,
    )

    resumed = approve_plan(
        session_id=created.session_id,
        repository_root=tmp_path,
        approved_by="operator",
        reason="approved for test",
    )

    assert resumed.session.status is AgentSessionStatus.COMPLETED
    assert len(resumed.session.stage_results) == 1