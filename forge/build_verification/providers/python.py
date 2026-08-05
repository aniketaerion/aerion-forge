"""Python build-verification providers."""

from __future__ import annotations

import sys
from pathlib import Path

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.providers.base import BuildVerificationProvider


class RuffProvider(BuildVerificationProvider):
    """Run Ruff through the active Python interpreter."""

    tool = VerificationTool.RUFF

    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        del repository_root, policy
        return (sys.executable, "-m", "ruff", "check", *step.arguments)


class MyPyProvider(BuildVerificationProvider):
    """Run MyPy through the active Python interpreter."""

    tool = VerificationTool.MYPY

    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        del repository_root, policy
        return (sys.executable, "-m", "mypy", *step.arguments)


class PytestProvider(BuildVerificationProvider):
    """Run pytest through the active Python interpreter."""

    tool = VerificationTool.PYTEST

    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        del repository_root, policy
        return (
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            *step.arguments,
        )


class PythonBuildProvider(BuildVerificationProvider):
    """Run `python -m build` without network access."""

    tool = VerificationTool.PYTHON_BUILD

    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        del repository_root

        if step.allow_network or policy.allow_network:
            raise BuildVerificationProviderError(
                "Python build verification must remain offline"
            )

        return (
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            *step.arguments,
        )