[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Write-Utf8NoBom "forge\agent_runtime\store.py" @'
"""Persistence for M3.8 Unified Agent Runtime."""

from __future__ import annotations

import json
from pathlib import Path

from forge.agent_runtime.errors import (
    AgentRuntimePersistenceError,
)
from forge.agent_runtime.models import (
    AgentCheckpoint,
    AgentEvent,
    AgentSession,
)


class AgentRuntimeStore:
    """Persist sessions, checkpoints, and telemetry atomically."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def _session_path(self, session_id: str) -> Path:
        return self.root / "sessions" / f"{session_id}.json"

    def _checkpoint_path(self, checkpoint_id: str) -> Path:
        return self.root / "checkpoints" / f"{checkpoint_id}.json"

    def _event_path(self, event_id: str) -> Path:
        return self.root / "events" / f"{event_id}.json"

    @staticmethod
    def _write_json(path: Path, payload: dict[str, object]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(path.suffix + ".tmp")
            temporary.write_text(
                json.dumps(payload, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            temporary.replace(path)
        except OSError as exc:
            raise AgentRuntimePersistenceError(
                f"unable to persist runtime artifact: {path}"
            ) from exc

    @staticmethod
    def _read_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise AgentRuntimePersistenceError(
                f"unable to read runtime artifact: {path}"
            ) from exc

    def save_session(self, session: AgentSession) -> Path:
        path = self._session_path(session.session_id)
        self._write_json(path, session.model_dump(mode="json"))
        return path

    def load_session(self, session_id: str) -> AgentSession:
        path = self._session_path(session_id)
        if not path.is_file():
            raise AgentRuntimePersistenceError(
                f"agent session not found: {session_id}"
            )
        return AgentSession.model_validate_json(self._read_text(path))

    def save_checkpoint(self, checkpoint: AgentCheckpoint) -> Path:
        path = self._checkpoint_path(checkpoint.checkpoint_id)
        self._write_json(path, checkpoint.model_dump(mode="json"))
        return path

    def load_checkpoint(self, checkpoint_id: str) -> AgentCheckpoint:
        path = self._checkpoint_path(checkpoint_id)
        if not path.is_file():
            raise AgentRuntimePersistenceError(
                f"agent checkpoint not found: {checkpoint_id}"
            )
        return AgentCheckpoint.model_validate_json(self._read_text(path))

    def append_event(self, event: AgentEvent) -> Path:
        path = self._event_path(event.event_id)
        self._write_json(path, event.model_dump(mode="json"))
        return path

    def list_session_ids(self) -> tuple[str, ...]:
        directory = self.root / "sessions"
        if not directory.is_dir():
            return ()
        return tuple(sorted(path.stem for path in directory.glob("*.json")))

    def list_event_ids(self) -> tuple[str, ...]:
        directory = self.root / "events"
        if not directory.is_dir():
            return ()
        return tuple(sorted(path.stem for path in directory.glob("*.json")))
'@

Write-Utf8NoBom "forge\agent_runtime\telemetry.py" @'
"""Telemetry for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from collections.abc import Mapping

from forge.agent_runtime.identifiers import agent_event_identifier
from forge.agent_runtime.models import (
    AgentEvent,
    AgentEventType,
)


def build_event(
    *,
    session_id: str,
    event_type: AgentEventType,
    message: str,
    stage_id: str | None = None,
    metadata: Mapping[str, str] | None = None,
) -> AgentEvent:
    payload = {
        "session_id": session_id,
        "event_type": event_type.value,
        "message": message,
        "stage_id": stage_id,
        "metadata": dict(metadata or {}),
    }

    return AgentEvent(
        event_id=agent_event_identifier(payload),
        session_id=session_id,
        event_type=event_type,
        message=message,
        stage_id=stage_id,
        metadata=dict(metadata or {}),
    )
'@

Write-Utf8NoBom "forge\agent_runtime\recovery.py" @'
"""Recovery helpers for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from forge.agent_runtime.errors import AgentRuntimeRecoveryError
from forge.agent_runtime.models import (
    AgentCheckpoint,
    AgentSession,
    AgentSessionStatus,
)


def recover_session(
    session: AgentSession,
    checkpoint: AgentCheckpoint,
) -> AgentSession:
    if session.session_id != checkpoint.session_id:
        raise AgentRuntimeRecoveryError(
            "checkpoint does not belong to the supplied session"
        )

    if checkpoint.status in {
        AgentSessionStatus.COMPLETED,
        AgentSessionStatus.FAILED,
        AgentSessionStatus.CANCELLED,
    }:
        raise AgentRuntimeRecoveryError(
            "terminal checkpoint cannot be resumed"
        )

    completed = set(checkpoint.completed_stage_ids)
    results = tuple(
        result
        for result in session.stage_results
        if result.stage_id in completed
    )

    return session.model_copy(
        update={
            "status": checkpoint.status,
            "current_stage_id": checkpoint.current_stage_id,
            "stage_results": results,
        }
    )
'@

Write-Utf8NoBom "forge\agent_runtime\reporting.py" @'
"""Reporting for M3.8 Unified Agent Runtime."""

from __future__ import annotations

import json
from pathlib import Path

from forge.agent_runtime.errors import AgentRuntimeReportError
from forge.agent_runtime.models import AgentSession


def render_markdown(session: AgentSession) -> str:
    lines = [
        "# Unified Agent Runtime Report",
        "",
        f"- Session ID: `{session.session_id}`",
        f"- Status: `{session.status.value}`",
        f"- Objective: {session.request.objective.objective}",
        f"- Completed stages: `{len(session.stage_results)}`",
        "",
        "## Stages",
        "",
    ]

    for stage in session.stages:
        result = next(
            (
                item
                for item in session.stage_results
                if item.stage_id == stage.stage_id
            ),
            None,
        )

        lines.extend(
            [
                f"### {stage.sequence}. {stage.name}",
                "",
                f"- Capability: `{stage.capability.value}`",
                (
                    f"- Status: `{result.status.value}`"
                    if result is not None
                    else "- Status: `pending`"
                ),
                (
                    f"- Summary: {result.summary}"
                    if result is not None
                    else "- Summary: not executed"
                ),
                "",
            ]
        )

    return "\n".join(lines)


def write_report_bundle(
    session: AgentSession,
    destination: Path,
) -> dict[str, Path]:
    try:
        destination.mkdir(parents=True, exist_ok=True)

        json_path = destination / "AGENT_SESSION.json"
        markdown_path = destination / "AGENT_SESSION_REPORT.md"

        json_path.write_text(
            json.dumps(
                session.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        markdown_path.write_text(
            render_markdown(session),
            encoding="utf-8",
        )
    except OSError as exc:
        raise AgentRuntimeReportError(
            f"unable to write agent runtime report: {exc}"
        ) from exc

    return {
        json_path.name: json_path,
        markdown_path.name: markdown_path,
    }
'@

Write-Utf8NoBom "tests\test_agent_runtime_store.py" @'
from pathlib import Path

from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
)
from forge.agent_runtime.store import AgentRuntimeStore


def session_for() -> AgentSession:
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )
    return AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.CREATED,
        stages=(stage,),
    )


def test_store_round_trip(tmp_path: Path) -> None:
    store = AgentRuntimeStore(tmp_path / "runtime")
    session = session_for()

    store.save_session(session)

    assert store.load_session(session.session_id) == session


def test_store_lists_sessions(tmp_path: Path) -> None:
    store = AgentRuntimeStore(tmp_path / "runtime")
    session = session_for()
    store.save_session(session)

    assert store.list_session_ids() == ("session-1",)
'@

Write-Utf8NoBom "tests\test_agent_runtime_telemetry.py" @'
from forge.agent_runtime.models import AgentEventType
from forge.agent_runtime.telemetry import build_event


def test_event_identifier_is_deterministic() -> None:
    first = build_event(
        session_id="session-1",
        event_type=AgentEventType.SESSION_CREATED,
        message="created",
    )
    second = build_event(
        session_id="session-1",
        event_type=AgentEventType.SESSION_CREATED,
        message="created",
    )

    assert first.event_id == second.event_id
'@

Write-Utf8NoBom "tests\test_agent_runtime_recovery.py" @'
import pytest

from forge.agent_runtime.errors import AgentRuntimeRecoveryError
from forge.agent_runtime.models import (
    AgentCapability,
    AgentCheckpoint,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
)
from forge.agent_runtime.recovery import recover_session


def session_for() -> AgentSession:
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )
    return AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.PAUSED,
        stages=(stage,),
    )


def test_recovery_restores_checkpoint_state() -> None:
    session = session_for()
    checkpoint = AgentCheckpoint(
        checkpoint_id="checkpoint-1",
        session_id=session.session_id,
        status=AgentSessionStatus.PAUSED,
        repository_revision="abc",
    )

    recovered = recover_session(session, checkpoint)

    assert recovered.status is AgentSessionStatus.PAUSED


def test_recovery_rejects_foreign_checkpoint() -> None:
    session = session_for()
    checkpoint = AgentCheckpoint(
        checkpoint_id="checkpoint-1",
        session_id="other-session",
        status=AgentSessionStatus.PAUSED,
        repository_revision="abc",
    )

    with pytest.raises(AgentRuntimeRecoveryError):
        recover_session(session, checkpoint)
'@

Write-Utf8NoBom "tests\test_agent_runtime_reporting.py" @'
from pathlib import Path

from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
)
from forge.agent_runtime.reporting import (
    render_markdown,
    write_report_bundle,
)


def session_for() -> AgentSession:
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.MISSION_PLANNING,
        name="Plan",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=AgentObjective(
            objective="Implement feature",
            repository_root=".",
        ),
    )
    return AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.CREATED,
        stages=(stage,),
    )


def test_markdown_contains_session_status() -> None:
    rendered = render_markdown(session_for())

    assert "Unified Agent Runtime Report" in rendered
    assert "created" in rendered


def test_report_bundle_writes_files(tmp_path: Path) -> None:
    written = write_report_bundle(
        session_for(),
        tmp_path / "reports",
    )

    assert set(written) == {
        "AGENT_SESSION.json",
        "AGENT_SESSION_REPORT.md",
    }
'@

Write-Host ""
Write-Host "M3.8 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_agent_runtime_store.py `
    .\tests\test_agent_runtime_recovery.py `
    .\tests\test_agent_runtime_reporting.py `
    .\tests\test_agent_runtime_telemetry.py `
    -p no:cacheprovider
Assert-CommandSuccess "M3.8 Package 3 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M3.8 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short

