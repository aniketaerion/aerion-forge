"""Bounded subprocess runner for M3.7 Build Verification."""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from forge.build_verification.errors import (
    BuildVerificationProviderError,
)
from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
)
from forge.build_verification.registry import (
    BuildVerificationProviderRegistry,
)


def _bounded_lines(
    text: str,
    limit: int,
) -> tuple[str, ...]:
    lines = text.splitlines()

    if len(lines) <= limit:
        return tuple(lines)

    return (
        *lines[:limit],
        f"... truncated {len(lines) - limit} lines ...",
    )


def run_step(
    repository_root: Path,
    step: VerificationStep,
    policy: BuildVerificationPolicy,
    registry: BuildVerificationProviderRegistry | None = None,
) -> VerificationStepResult:
    """Execute exactly one registered verification step."""
    root = repository_root.resolve()
    working_directory = (root / step.working_directory).resolve()

    try:
        working_directory.relative_to(root)
    except ValueError as exc:
        raise BuildVerificationProviderError(
            f"step working directory escapes repository: {step.step_id}"
        ) from exc

    if not working_directory.is_dir():
        raise BuildVerificationProviderError(
            f"step working directory does not exist: {step.step_id}"
        )

    selected_registry = registry or BuildVerificationProviderRegistry()
    provider = selected_registry.get(step.tool)
    command = provider.command(step, root, policy)

    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    environment["NO_COLOR"] = "1"

    started_at = datetime.now(UTC)
    started = monotonic()

    try:
        completed = subprocess.run(
            command,
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=step.timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration = monotonic() - started
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else exc.stdout
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr

        return VerificationStepResult(
            step_id=step.step_id,
            status=VerificationStatus.TIMED_OUT,
            exit_code=None,
            duration_seconds=duration,
            stdout=_bounded_lines(
                stdout or "",
                policy.max_output_lines,
            ),
            stderr=_bounded_lines(
                stderr or "",
                policy.max_output_lines,
            ),
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
    except OSError as exc:
        raise BuildVerificationProviderError(
            f"unable to execute verification step {step.step_id}: {exc}"
        ) from exc

    duration = monotonic() - started
    status = (
        VerificationStatus.PASSED
        if completed.returncode == 0
        else VerificationStatus.FAILED
    )

    return VerificationStepResult(
        step_id=step.step_id,
        status=status,
        exit_code=completed.returncode,
        duration_seconds=duration,
        stdout=_bounded_lines(
            completed.stdout,
            policy.max_output_lines,
        ),
        stderr=_bounded_lines(
            completed.stderr,
            policy.max_output_lines,
        ),
        started_at=started_at,
        completed_at=datetime.now(UTC),
    )