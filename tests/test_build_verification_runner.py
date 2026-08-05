from pathlib import Path

from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStatus,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.runner import run_step


def test_runner_executes_passing_ruff_step(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("value = 1\n", encoding="utf-8")

    step = VerificationStep(
        step_id="ruff-pass",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("sample.py",),
        timeout_seconds=30,
    )

    result = run_step(
        tmp_path,
        step,
        BuildVerificationPolicy(),
    )

    assert result.status is VerificationStatus.PASSED
    assert result.exit_code == 0


def test_runner_captures_failed_ruff_step(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("import os\n", encoding="utf-8")

    step = VerificationStep(
        step_id="ruff-fail",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("sample.py",),
        timeout_seconds=30,
    )

    result = run_step(
        tmp_path,
        step,
        BuildVerificationPolicy(),
    )

    assert result.status is VerificationStatus.FAILED
    assert result.exit_code != 0
    assert any("F401" in line for line in result.stdout)