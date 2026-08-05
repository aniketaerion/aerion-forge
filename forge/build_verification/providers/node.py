"""Node build-verification providers."""

from __future__ import annotations

from pathlib import Path

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.providers.base import BuildVerificationProvider


class _NodeScriptProvider(BuildVerificationProvider):
    script_name: str

    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        package_json = repository_root / step.working_directory / "package.json"

        if not package_json.is_file():
            raise BuildVerificationProviderError(
                f"package.json not found for step: {step.step_id}"
            )

        if step.allow_network or policy.allow_network:
            raise BuildVerificationProviderError(
                "Node build verification must remain offline"
            )

        return (
            "npm",
            "run",
            self.script_name,
            "--",
            *step.arguments,
        )


class NodeLintProvider(_NodeScriptProvider):
    """Run the repository's Node lint script."""

    tool = VerificationTool.NODE_LINT
    script_name = "lint"


class NodeTestProvider(_NodeScriptProvider):
    """Run the repository's Node test script."""

    tool = VerificationTool.NODE_TEST
    script_name = "test"


class NodeBuildProvider(_NodeScriptProvider):
    """Run the repository's Node build script."""

    tool = VerificationTool.NODE_BUILD
    script_name = "build"