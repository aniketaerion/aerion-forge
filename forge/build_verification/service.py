"""Application service for M3.7 Build Verification."""

from __future__ import annotations

import subprocess
from pathlib import Path

from forge.build_verification.identifiers import (
    verification_request_identifier,
    verification_step_identifier,
)
from forge.build_verification.models import (
    BuildVerificationPolicy,
    BuildVerificationRequest,
    ReleaseGateDecision,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.pipeline import BuildVerificationPipeline
from forge.build_verification.policies import (
    resolve_repository_root,
    validate_target_paths,
)
from forge.build_verification.reporting import write_report_bundle
from forge.build_verification.store import BuildVerificationStore


class BuildVerificationService:
    """Coordinate request creation, execution, persistence, and reporting."""

    def __init__(
        self,
        policy: BuildVerificationPolicy | None = None,
    ) -> None:
        self.policy = policy or BuildVerificationPolicy()
        self.pipeline = BuildVerificationPipeline(self.policy)

    @staticmethod
    def source_revision(repository_root: Path) -> str:
        """Return the current Git revision."""
        completed = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            cwd=repository_root,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
        )

        if completed.returncode != 0:
            raise ValueError("unable to resolve repository source revision")

        return completed.stdout.strip()

    def create_request(
        self,
        repository_root: str | Path,
        *,
        objective: str,
        tools: tuple[VerificationTool, ...],
        target_paths: tuple[str, ...] = (),
    ) -> BuildVerificationRequest:
        """Create a deterministic verification request."""
        root = resolve_repository_root(repository_root)
        normalized_paths = validate_target_paths(root, target_paths)
        revision = self.source_revision(root)

        steps = tuple(
            VerificationStep(
                step_id=verification_step_identifier(
                    {
                        "tool": tool.value,
                        "position": index,
                        "target_paths": normalized_paths,
                    }
                ),
                tool=tool,
                name=tool.value.replace("_", " ").title(),
                arguments=normalized_paths or (".",),
            )
            for index, tool in enumerate(tools, start=1)
        )

        request_id = verification_request_identifier(
            {
                "repository_root": str(root),
                "source_revision": revision,
                "objective": objective,
                "tools": [tool.value for tool in tools],
                "target_paths": normalized_paths,
            }
        )

        return BuildVerificationRequest(
            request_id=request_id,
            repository_root=str(root),
            source_revision=revision,
            objective=objective,
            steps=steps,
            target_paths=normalized_paths,
        )

    def verify(
        self,
        request: BuildVerificationRequest,
        *,
        store: BuildVerificationStore | None = None,
        report_directory: Path | None = None,
    ) -> ReleaseGateDecision:
        """Execute verification and optionally persist all artifacts."""
        evidence, decision = self.pipeline.execute(request)

        if store is not None:
            store.save_evidence(evidence)
            store.save_decision(decision)

        if report_directory is not None:
            write_report_bundle(
                evidence,
                decision,
                report_directory,
            )

        return decision