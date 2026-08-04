"""Service orchestration for M3.5 Autonomous Repair."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from forge.autonomous_repair.errors import (
    RepairInputValidationError,
    RepairPersistenceError,
)
from forge.autonomous_repair.executor import (
    AutonomousRepairExecutor,
    ValidationCallback,
    repository_fingerprint,
)
from forge.autonomous_repair.identifiers import (
    execution_request_identifier,
    execution_session_identifier,
)
from forge.autonomous_repair.models import (
    RepairApproval,
    RepairExecutionReport,
    RepairExecutionRequest,
    RepairExecutionSession,
    RepairExecutionStatus,
    RepairInput,
    RepairProposal,
)
from forge.autonomous_repair.policies import AutonomousRepairPolicy
from forge.autonomous_repair.registry import RepairProviderRegistry
from forge.autonomous_repair.reporting import write_report_bundle


class AutonomousRepairService:
    """Create proposals, execute repairs and persist evidence."""

    def __init__(
        self,
        *,
        policy: AutonomousRepairPolicy | None = None,
        registry: RepairProviderRegistry | None = None,
        executor: AutonomousRepairExecutor | None = None,
    ) -> None:
        self.policy = policy or AutonomousRepairPolicy()
        self.registry = registry or RepairProviderRegistry.with_builtins()
        self.executor = executor or AutonomousRepairExecutor(self.policy)

    def load_input(self, path: Path) -> RepairInput:
        """Load immutable repair input from JSON."""
        try:
            return RepairInput.model_validate_json(
                path.read_text(encoding="utf-8-sig")
            )
        except (OSError, ValidationError) as exc:
            raise RepairInputValidationError(
                f"unable to load repair input {path}: {exc}"
            ) from exc

    def propose(self, repair_input: RepairInput) -> RepairProposal:
        """Resolve provider and build one bounded proposal."""
        root = self.policy.resolve_repository(Path(repair_input.repository_root))
        self.policy.validate_provider(repair_input.provider)
        provider = self.registry.get(repair_input.provider)
        if not provider.supports(repair_input):
            raise RepairInputValidationError(
                f"provider does not support input: {repair_input.provider}"
            )
        return provider.propose(root, repair_input, self.policy)

    def create_session(
        self,
        repair_input: RepairInput,
    ) -> RepairExecutionSession:
        """Create one bounded execution session."""
        session_id = execution_session_identifier(
            {
                "input_id": repair_input.input_id,
                "candidate_id": repair_input.candidate_id,
                "provider": repair_input.provider.value,
                "repository_fingerprint": repair_input.repository_fingerprint,
            }
        )
        return RepairExecutionSession(
            session_id=session_id,
            input=repair_input,
            max_attempts=self.policy.max_attempts,
            status=RepairExecutionStatus.CREATED,
        )

    def build_request(
        self,
        proposal: RepairProposal,
        *,
        repository_root: Path,
        dry_run: bool,
        approval: RepairApproval | None = None,
    ) -> RepairExecutionRequest:
        """Build a dry-run or approved execution request."""
        fingerprint = repository_fingerprint(
            repository_root,
            proposal.affected_paths,
        )
        request_id = execution_request_identifier(
            {
                "proposal_id": proposal.proposal_id,
                "repository_fingerprint": fingerprint,
                "dry_run": dry_run,
                "approved": bool(approval and approval.approved),
            }
        )
        return RepairExecutionRequest(
            request_id=request_id,
            proposal=proposal,
            repository_root=str(repository_root.resolve()),
            repository_fingerprint=fingerprint,
            dry_run=dry_run,
            approval=approval or RepairApproval(),
        )

    def execute(
        self,
        request: RepairExecutionRequest,
        *,
        attempt_number: int = 1,
        validate: ValidationCallback | None = None,
    ) -> RepairExecutionReport:
        """Execute one bounded repair and return final evidence."""
        attempt = self.executor.execute(
            request,
            attempt_number=attempt_number,
            validate=validate,
        )
        succeeded = attempt.status is RepairExecutionStatus.SUCCEEDED
        return RepairExecutionReport(
            session_id=execution_session_identifier(
                {
                    "proposal_id": request.proposal.proposal_id,
                    "request_id": request.request_id,
                }
            ),
            status=attempt.status,
            succeeded=succeeded,
            attempts=(attempt,),
            final_repository_fingerprint=repository_fingerprint(
                Path(request.repository_root),
                request.proposal.affected_paths,
            ),
            messages=(
                "Dry-run completed without mutation."
                if request.dry_run
                else "Approved repair applied and validated.",
            ),
        )

    def save_input(self, repair_input: RepairInput, destination: Path) -> Path:
        """Persist repair input as JSON."""
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(
                    repair_input.model_dump(mode="json"),
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            raise RepairPersistenceError(
                f"unable to save repair input {destination}: {exc}"
            ) from exc
        return destination

    @staticmethod
    def write_reports(
        report: RepairExecutionReport,
        destination: Path,
    ) -> dict[str, Path]:
        """Persist a repair report bundle."""
        return write_report_bundle(report, destination)