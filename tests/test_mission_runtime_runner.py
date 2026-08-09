from pathlib import Path

from forge.agent_runtime.models import AgentSessionStatus
from forge.mission_runtime.runner import (
    approve_current_boundary,
    load_session,
    run_objective,
)

OBJECTIVE = (
    "Add subtract(a: int, b: int) -> int "
    "to src/calculator.py and change nothing else."
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()
    (tmp_path / "src").mkdir()

    (tmp_path / "src" / "calculator.py").write_text(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n",
        encoding="utf-8",
    )


def test_runner_stops_at_plan_approval(tmp_path: Path) -> None:
    initialize_repository(tmp_path)

    result = run_objective(
        objective=OBJECTIVE,
        repository_root=tmp_path,
    )

    assert result.session.status is AgentSessionStatus.AWAITING_APPROVAL

    persisted = load_session(
        session_id=result.session_id,
        repository_root=tmp_path,
    )

    assert persisted.session_id == result.session_id


def test_runner_advances_to_edit_approval_after_plan_approval(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    created = run_objective(
        objective=OBJECTIVE,
        repository_root=tmp_path,
    )

    resumed = approve_current_boundary(
        session_id=created.session_id,
        repository_root=tmp_path,
        approved_by="operator",
        reason="approved for test",
    )

    assert resumed.session.status is AgentSessionStatus.AWAITING_APPROVAL
    assert len(resumed.session.stage_results) == 2
