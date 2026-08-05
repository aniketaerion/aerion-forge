import sys
from pathlib import Path

import pytest

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.providers.python import (
    PytestProvider,
    PythonBuildProvider,
    RuffProvider,
)


def test_ruff_provider_uses_active_python(tmp_path: Path) -> None:
    step = VerificationStep(
        step_id="ruff",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=(".",),
    )

    command = RuffProvider().command(
        step,
        tmp_path,
        BuildVerificationPolicy(),
    )

    assert command[:4] == (sys.executable, "-m", "ruff", "check")


def test_pytest_provider_disables_cache_provider(tmp_path: Path) -> None:
    step = VerificationStep(
        step_id="pytest",
        tool=VerificationTool.PYTEST,
        name="Pytest",
    )

    command = PytestProvider().command(
        step,
        tmp_path,
        BuildVerificationPolicy(),
    )

    assert command[3:5] == ("-p", "no:cacheprovider")


def test_python_build_provider_rejects_network(tmp_path: Path) -> None:
    step = VerificationStep(
        step_id="build",
        tool=VerificationTool.PYTHON_BUILD,
        name="Build",
        allow_network=True,
    )

    with pytest.raises(BuildVerificationProviderError):
        PythonBuildProvider().command(
            step,
            tmp_path,
            BuildVerificationPolicy(allow_network=True),
        )