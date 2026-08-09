"""Bounded production executors for M5.8 Package 5B.

This module proves the real Safe Code Editing and Build Verification path for
an explicitly bounded function-addition mission. Unsupported edit grammars
fail closed instead of being fabricated.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.agent_runtime.adapters.base import failed_result, succeeded_result
from forge.agent_runtime.models import AgentSession, AgentStage, AgentStageResult
from forge.build_verification.models import (
    BuildVerificationPolicy,
    ReleaseDecision,
    VerificationTool,
)
from forge.build_verification.service import BuildVerificationService
from forge.safe_code_editing.loader import load_text_file
from forge.safe_code_editing.models import (
    EditOperation,
    EditOperationType,
    FileEditPlan,
    SafeEditRequest,
)
from forge.safe_code_editing.policies import SafeEditPolicy
from forge.safe_code_editing.service import SafeCodeEditingService

_FUNCTION_ADD_RE = re.compile(
    r"^\s*Add\s+"
    r"(?P<name>[A-Za-z_]\w*)"
    r"\((?P<params>[^)]*)\)"
    r"\s*->\s*(?P<return_type>[A-Za-z_][A-Za-z0-9_\[\], .|]*)"
    r"\s+to\s+"
    r"(?P<path>[A-Za-z0-9_./\\-]+)"
    r"\s+and\s+change\s+nothing\s+else\.?\s*$",
    re.IGNORECASE,
)


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def _parse_parameter_names(params: str) -> tuple[str, ...]:
    names: list[str] = []
    for item in params.split(","):
        candidate = item.strip()
        if not candidate:
            continue
        name = candidate.split(":", 1)[0].strip()
        if not re.fullmatch(r"[A-Za-z_]\w*", name):
            raise ValueError(f"unsupported parameter declaration: {candidate}")
        names.append(name)
    return tuple(names)


def _bounded_function_change(objective: str) -> tuple[str, str, str]:
    match = _FUNCTION_ADD_RE.fullmatch(objective)
    if match is None:
        raise ValueError(
            "Package 5B accepts only 'Add name(args) -> type to path.py "
            "and change nothing else.'"
        )

    name = match.group("name")
    params = match.group("params").strip()
    return_type = match.group("return_type").strip()
    relative_path = match.group("path").replace("\\", "/")
    parameter_names = _parse_parameter_names(params)
    if len(parameter_names) != 2:
        raise ValueError("bounded arithmetic acceptance requires two parameters")

    left, right = parameter_names
    operators = {
        "add": "+",
        "subtract": "-",
        "multiply": "*",
        "divide": "/",
    }
    operator = operators.get(name.lower())
    if operator is None:
        raise ValueError(
            "Package 5B acceptance supports add/subtract/multiply/divide only"
        )

    rendered = (
        f"def {name}({params}) -> {return_type}:\n"
        f"    return {left} {operator} {right}\n"
    )
    return relative_path, name, rendered


def planning_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, Any],
) -> AgentStageResult:
    del context
    try:
        relative_path, function_name, _ = _bounded_function_change(
            session.request.objective.objective
        )
        if not (repository_root / relative_path).is_file():
            return failed_result(stage, f"target does not exist: {relative_path}")
        return succeeded_result(
            stage,
            f"bounded plan prepared for {relative_path}",
            evidence={"target_path": relative_path, "function_name": function_name},
        )
    except ValueError as exc:
        return failed_result(stage, f"planning rejected objective: {exc}")


def impact_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, Any],
) -> AgentStageResult:
    del context
    try:
        relative_path, function_name, _ = _bounded_function_change(
            session.request.objective.objective
        )
        content = (repository_root / relative_path).read_text(encoding="utf-8-sig")
        if re.search(rf"(?m)^\s*def\s+{re.escape(function_name)}\s*\(", content):
            return failed_result(stage, f"function already exists: {function_name}")
        return succeeded_result(
            stage,
            "impact analysis restricted the mission to one source file",
            evidence={"target_path": relative_path, "scope": "single_file"},
        )
    except (OSError, ValueError) as exc:
        return failed_result(stage, f"impact analysis failed: {exc}")


def change_planning_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, Any],
) -> AgentStageResult:
    del context
    try:
        relative_path, _, rendered = _bounded_function_change(
            session.request.objective.objective
        )
        loaded = load_text_file(repository_root, relative_path, SafeEditPolicy())
        return succeeded_result(
            stage,
            "safe edit plan validated against source fingerprint",
            evidence={
                "target_path": relative_path,
                "source_fingerprint": loaded.fingerprint,
                "planned_insert_bytes": str(len(rendered.encode("utf-8"))),
            },
        )
    except Exception as exc:
        return failed_result(stage, f"safe-change planning failed: {exc}")


def editing_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, Any],
) -> AgentStageResult:
    del context
    try:
        relative_path, function_name, rendered = _bounded_function_change(
            session.request.objective.objective
        )
        policy = SafeEditPolicy()
        loaded = load_text_file(repository_root, relative_path, policy)

        separator = ""
        if loaded.content:
            if not loaded.content.endswith(("\n", "\r")):
                separator = loaded.newline * 2
            elif not loaded.content.endswith(loaded.newline * 2):
                separator = loaded.newline
        insertion = separator + rendered.replace("\n", loaded.newline)

        operation = EditOperation(
            operation_id=_stable_id(
                "edit-operation",
                session.session_id + relative_path + loaded.fingerprint + insertion,
            ),
            operation_type=EditOperationType.INSERT,
            relative_path=relative_path,
            start_offset=len(loaded.content),
            end_offset=len(loaded.content),
            replacement_text=insertion,
            source_fingerprint=loaded.fingerprint,
        )
        file_plan = FileEditPlan(
            relative_path=relative_path,
            source_fingerprint=loaded.fingerprint,
            operations=(operation,),
        )
        request = SafeEditRequest(
            request_id=_stable_id("safe-edit-request", session.session_id + operation.operation_id),
            change_plan_id=_stable_id("change-plan", session.session_id + relative_path),
            repository_root=str(repository_root),
            file_plans=(file_plan,),
            dry_run=False,
            approved=True,
        )

        report = SafeCodeEditingService(policy).execute(request)
        changed = tuple(item.relative_path for item in report.file_results if item.changed)
        if changed != (relative_path,):
            return failed_result(
                stage,
                "safe editor did not produce exactly the approved file change",
                evidence={"changed_paths": ",".join(changed)},
            )

        return succeeded_result(
            stage,
            f"safe code edit added {function_name} to {relative_path}",
            artifact_paths=(relative_path,),
            evidence={
                "target_path": relative_path,
                "transaction_id": report.transaction_id,
            },
        )
    except Exception as exc:
        return failed_result(stage, f"safe code editing failed: {exc}")


def verification_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, Any],
) -> AgentStageResult:
    del context
    try:
        policy = BuildVerificationPolicy(
            allowed_tools=(VerificationTool.PYTEST,),
            require_clean_working_tree=False,
        )
        service = BuildVerificationService(policy)
        request = service.create_request(
            repository_root,
            objective=session.request.objective.objective,
            tools=(VerificationTool.PYTEST,),
        )
        decision = service.verify(request)
        if decision.decision is not ReleaseDecision.APPROVED:
            return failed_result(
                stage,
                "build verification rejected the edited repository",
                evidence={
                    "decision": decision.decision.value,
                    "decision_id": decision.decision_id,
                },
            )
        return succeeded_result(
            stage,
            "target repository pytest verification passed",
            evidence={
                "decision": decision.decision.value,
                "decision_id": decision.decision_id,
                "evidence_id": decision.evidence_id,
            },
        )
    except Exception as exc:
        return failed_result(stage, f"build verification failed: {exc}")