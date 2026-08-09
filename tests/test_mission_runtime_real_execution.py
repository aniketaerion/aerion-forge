from __future__ import annotations

import subprocess
from pathlib import Path

from pytest import MonkeyPatch

from forge.agent_runtime.models import AgentSessionStatus
from forge.mission_runtime.runner import (
    approve_current_boundary,
    run_objective,
)

OBJECTIVE = (
    "Add subtract(a: int, b: int) -> int "
    "to src/calculator.py and change nothing else."
)


def _run_git(root: Path, *args: str) -> None:
    completed = subprocess.run(
        ("git", *args),
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
        shell=False,
    )
    assert completed.returncode == 0, completed.stderr


def _initialize_acceptance_repository(root: Path) -> None:
    (root / "src").mkdir()
    (root / "tests").mkdir()

    (root / "src" / "calculator.py").write_text(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_calculator.py").write_text(
        "from src.calculator import add\n\n\n"
        "def test_add() -> None:\n"
        "    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )
    (root / "pyproject.toml").write_text(
        "[project]\n"
        'name = "forge-package5b-acceptance"\n'
        'version = "0.1.0"\n'
        'requires-python = ">=3.11"\n\n'
        "[tool.pytest.ini_options]\n"
        'pythonpath = ["."]\n',
        encoding="utf-8",
    )

    _run_git(root, "init")
    _run_git(root, "config", "user.email", "forge@example.invalid")
    _run_git(root, "config", "user.name", "Aerion Forge Test")
    _run_git(root, "add", ".")
    _run_git(root, "commit", "-m", "baseline")


def test_real_bounded_edit_and_verification(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    repository = tmp_path / "acceptance"
    repository.mkdir()
    _initialize_acceptance_repository(repository)

    state_root = tmp_path / "runtime-state"
    monkeypatch.setenv(
        "AERION_FORGE_RUNTIME_STATE_ROOT",
        str(state_root),
    )

    first = run_objective(
        objective=OBJECTIVE,
        repository_root=repository,
    )
    assert first.session.status is AgentSessionStatus.AWAITING_APPROVAL

    after_plan = approve_current_boundary(
        session_id=first.session_id,
        repository_root=repository,
        approved_by="operator",
        reason="plan approved",
    )
    assert after_plan.session.status is AgentSessionStatus.AWAITING_APPROVAL

    after_edit = approve_current_boundary(
        session_id=first.session_id,
        repository_root=repository,
        approved_by="operator",
        reason="edit approved",
    )
    assert after_edit.session.status is AgentSessionStatus.AWAITING_APPROVAL

    calculator = (repository / "src" / "calculator.py").read_text(
        encoding="utf-8"
    )
    assert "def subtract(a: int, b: int) -> int:" in calculator
    assert "return a - b" in calculator

    completed = approve_current_boundary(
        session_id=first.session_id,
        repository_root=repository,
        approved_by="operator",
        reason="release approved",
    )
    assert completed.session.status is AgentSessionStatus.COMPLETED

    changed = subprocess.run(
        ("git", "status", "--short"),
        cwd=repository,
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    ).stdout.splitlines()

    assert changed == [" M src/calculator.py"]
    assert not (repository / "memory").exists()
