"""In-memory mission runtime repository."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.mission_runtime.models import (
    MissionApproval,
    MissionCheckpoint,
    MissionEvidence,
    MissionResult,
    MissionSession,
)


@dataclass(slots=True)
class InMemoryMissionRepository:
    sessions: dict[str, MissionSession] = field(default_factory=dict)
    approvals: dict[str, MissionApproval] = field(default_factory=dict)
    checkpoints: dict[str, MissionCheckpoint] = field(default_factory=dict)
    evidence: dict[str, MissionEvidence] = field(default_factory=dict)
    results: dict[str, MissionResult] = field(default_factory=dict)

    def put_session(self, session: MissionSession) -> None:
        self.sessions[session.session_id] = session

    def get_session(self, session_id: str) -> MissionSession | None:
        return self.sessions.get(session_id)

    def put_approval(self, approval: MissionApproval) -> None:
        self.approvals[approval.approval_id] = approval

    def put_checkpoint(self, checkpoint: MissionCheckpoint) -> None:
        self.checkpoints[checkpoint.checkpoint_id] = checkpoint

    def put_evidence(self, evidence: MissionEvidence) -> None:
        self.evidence[evidence.evidence_id] = evidence

    def put_result(self, result: MissionResult) -> None:
        self.results[result.result_id] = result