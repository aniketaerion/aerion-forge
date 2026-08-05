"""Application service for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from forge.agent_runtime.executor import AgentRuntimeExecutor
from forge.agent_runtime.identifiers import (
    agent_request_identifier,
    agent_session_identifier,
    agent_stage_identifier,
)
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentRuntimePolicy,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    ApprovalKind,
)
from forge.agent_runtime.policies import (
    resolve_repository_root,
    validate_request,
    validate_self_modification,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry

_DEFAULT_PIPELINE: tuple[
    tuple[AgentCapability, str, ApprovalKind | None],
    ...,
] = (
    (
        AgentCapability.MISSION_PLANNING,
        "Mission Planning",
        ApprovalKind.PLAN,
    ),
    (
        AgentCapability.IMPACT_ANALYSIS,
        "Impact Analysis",
        None,
    ),
    (
        AgentCapability.SAFE_CHANGE_PLANNING,
        "Safe Change Planning",
        ApprovalKind.EDIT,
    ),
    (
        AgentCapability.SAFE_CODE_EDITING,
        "Safe Code Editing",
        ApprovalKind.EDIT,
    ),
    (
        AgentCapability.AUTONOMOUS_REPAIR,
        "Autonomous Repair",
        ApprovalKind.REPAIR,
    ),
    (
        AgentCapability.BUILD_VERIFICATION,
        "Build Verification",
        ApprovalKind.RELEASE,
    ),
)


class AgentRuntimeService:
    """Create and operate unified engineering-agent sessions."""

    def __init__(
        self,
        registry: AgentCapabilityRegistry,
        policy: AgentRuntimePolicy | None = None,
    ) -> None:
        self.registry = registry
        self.policy = policy or AgentRuntimePolicy()
        self.executor = AgentRuntimeExecutor(
            registry,
            self.policy,
        )

    def create_request(
        self,
        objective: AgentObjective,
        *,
        dry_run: bool = True,
        allow_code_changes: bool = False,
        max_stages: int | None = None,
        max_repair_attempts: int | None = None,
    ) -> AgentRuntimeRequest:
        """Create and validate one deterministic runtime request."""
        root = resolve_repository_root(
            objective.repository_root
        )
        validate_self_modification(
            root,
            objective.target_paths,
            self.policy,
        )

        payload = {
            "objective": objective.objective,
            "repository_root": str(root),
            "target_paths": objective.target_paths,
            "constraints": objective.constraints,
            "acceptance_criteria": objective.acceptance_criteria,
            "requested_capabilities": [
                capability.value
                for capability
                in objective.requested_capabilities
            ],
            "dry_run": dry_run,
            "allow_code_changes": allow_code_changes,
        }

        request = AgentRuntimeRequest(
            request_id=agent_request_identifier(payload),
            objective=objective.model_copy(
                update={"repository_root": str(root)}
            ),
            dry_run=dry_run,
            allow_code_changes=allow_code_changes,
            max_stages=(
                max_stages
                if max_stages is not None
                else self.policy.max_stages
            ),
            max_repair_attempts=(
                max_repair_attempts
                if max_repair_attempts is not None
                else self.policy.max_repair_attempts
            ),
        )
        validate_request(request, self.policy)
        return request

    def create_session(
        self,
        request: AgentRuntimeRequest,
    ) -> AgentSession:
        """Create a deterministic runtime session and stage graph."""
        requested = (
            request.objective.requested_capabilities
            or tuple(
                capability
                for capability, _, _
                in _DEFAULT_PIPELINE
            )
        )

        definitions = tuple(
            definition
            for definition in _DEFAULT_PIPELINE
            if definition[0] in requested
        )

        self.registry.validate_required(
            capability
            for capability, _, _
            in definitions
        )

        stages: list[AgentStage] = []
        previous_stage_id: str | None = None

        for sequence, (
            capability,
            name,
            approval,
        ) in enumerate(definitions, start=1):
            stage_id = agent_stage_identifier(
                {
                    "request_id": request.request_id,
                    "sequence": sequence,
                    "capability": capability.value,
                }
            )
            stages.append(
                AgentStage(
                    stage_id=stage_id,
                    sequence=sequence,
                    capability=capability,
                    name=name,
                    requires_approval=approval,
                    depends_on=(
                        (previous_stage_id,)
                        if previous_stage_id is not None
                        else ()
                    ),
                )
            )
            previous_stage_id = stage_id

        session_id = agent_session_identifier(
            {
                "request_id": request.request_id,
                "stage_ids": [
                    stage.stage_id for stage in stages
                ],
            }
        )

        return AgentSession(
            session_id=session_id,
            request=request,
            status=AgentSessionStatus.CREATED,
            stages=tuple(stages),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def add_approval(
        self,
        session: AgentSession,
        approval: AgentApproval,
    ) -> AgentSession:
        """Append one immutable human approval to a session."""
        if any(
            existing.approval_id == approval.approval_id
            for existing in session.approvals
        ):
            return session

        return session.model_copy(
            update={
                "approvals": (
                    *session.approvals,
                    approval,
                ),
                "updated_at": datetime.now(UTC),
            }
        )

    def run_next(
        self,
        session: AgentSession,
        *,
        context: dict[str, object] | None = None,
    ) -> AgentSession:
        """Execute exactly one runtime stage."""
        return self.executor.run_next(
            session,
            repository_root=Path(
                session.request.objective.repository_root
            ),
            context=context or {},
        )

    def run_to_boundary(
        self,
        session: AgentSession,
        *,
        context: dict[str, object] | None = None,
    ) -> AgentSession:
        """Execute until approval, failure, or completion."""
        return self.executor.run_to_boundary(
            session,
            repository_root=Path(
                session.request.objective.repository_root
            ),
            context=context or {},
        )