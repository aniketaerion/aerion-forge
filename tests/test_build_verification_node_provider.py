from pathlib import Path

import pytest

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.providers.node import (
    NodeBuildProvider,
    NodeLintProvider,
)


def test_node_lint_provider_builds_npm_command(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    step = VerificationStep(
        step_id="lint",
        tool=VerificationTool.NODE_LINT,
        name="Node lint",
        arguments=("--silent",),
    )

    command = NodeLintProvider().command(
        step,
        tmp_path,
        BuildVerificationPolicy(),
    )

    assert command == ("npm", "run", "lint", "--", "--silent")


def test_node_provider_requires_package_json(tmp_path: Path) -> None:
    step = VerificationStep(
        step_id="build",
        tool=VerificationTool.NODE_BUILD,
        name="Node build",
    )

    with pytest.raises(BuildVerificationProviderError):
        NodeBuildProvider().command(
            step,
            tmp_path,
            BuildVerificationPolicy(),
        )