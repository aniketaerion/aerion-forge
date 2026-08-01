"""Runtime and target diagnostic orchestration."""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

from forge.capabilities.catalogue import built_in_catalogue
from forge.configuration.models import ConfigurationSnapshot
from forge.configuration.resolver import ConfigurationResolver
from forge.diagnostics.checks import DiagnosticContext, execute, skipped
from forge.diagnostics.errors import DiagnosticsDisabledError
from forge.diagnostics.models import (
    CATALOGUE_VERSION,
    SCHEMA_VERSION,
    DiagnosticCategory,
    DiagnosticChange,
    DiagnosticChangeSet,
    DiagnosticChangeType,
    DiagnosticConfiguration,
    DiagnosticGeneration,
    DiagnosticResult,
    DiagnosticResultSet,
    DiagnosticScope,
    DiagnosticSnapshot,
    HealthStatus,
)
from forge.diagnostics.registry import DIAGNOSTIC_REGISTRY
from forge.diagnostics.renderer import DiagnosticRenderer
from forge.diagnostics.resolver import resolve_target
from forge.diagnostics.store import DiagnosticRepository
from forge.diagnostics.validator import aggregate, require_valid_definitions, statistics


class DiagnosticService:
    def __init__(
        self,
        root: Path,
        memory_path: Path,
        reports_path: Path,
        configuration: DiagnosticConfiguration | None = None,
        logger: logging.Logger | None = None,
        renderer: DiagnosticRenderer | None = None,
    ) -> None:
        self.root = root.resolve()
        self.memory_path = memory_path.resolve()
        self.reports_path = reports_path.resolve()
        self.configuration = configuration or DiagnosticConfiguration()
        self.logger = logger or logging.getLogger("forge.diagnostics")
        self.store = DiagnosticRepository(
            self.memory_path / "diagnostics.json", self.configuration.history_limit
        )
        self.renderer = renderer or DiagnosticRenderer()

    def health(
        self,
        *,
        categories: tuple[DiagnosticCategory, ...] = (),
        check_id: str | None = None,
        persist: bool = True,
        reports: bool = True,
        strict: bool | None = None,
    ) -> DiagnosticResultSet:
        return self._run(None, categories, check_id, persist, reports, strict)

    def diagnose(
        self,
        target: str | None = None,
        *,
        categories: tuple[DiagnosticCategory, ...] = (),
        check_id: str | None = None,
        persist: bool = True,
        reports: bool = True,
        strict: bool | None = None,
    ) -> DiagnosticResultSet:
        return self._run(target, categories, check_id, persist, reports, strict, target_mode=True)

    def _run(
        self,
        target: str | None,
        categories: tuple[DiagnosticCategory, ...],
        check_id: str | None,
        persist: bool,
        reports: bool,
        strict: bool | None,
        target_mode: bool = False,
    ) -> DiagnosticResultSet:
        if not self.configuration.enabled:
            raise DiagnosticsDisabledError("Runtime diagnostics are disabled.")
        definitions = DIAGNOSTIC_REGISTRY.list_checks()
        require_valid_definitions(definitions)
        selected = self._select(definitions, target_mode, categories, check_id)
        configuration = ConfigurationResolver(self.root).resolve(environment={})
        resolved_target = (
            resolve_target(target, self.memory_path / "workspaces.json", self.logger)
            if target_mode
            else None
        )
        context = DiagnosticContext(
            root=self.root,
            memory_path=self.memory_path,
            reports_path=self.reports_path,
            configuration_valid=configuration.validation.valid,
            configuration_fingerprint=configuration.configuration_fingerprint,
            strict=self.configuration.strict if strict is None else strict,
            write_probe_enabled=self.configuration.write_probe_enabled,
            target_root=resolved_target.root if resolved_target else None,
            target_identity=resolved_target.identity if resolved_target else None,
            workspace_id=(
                resolved_target.workspace.workspace_id
                if resolved_target and resolved_target.workspace
                else None
            ),
            project_type=(
                resolved_target.workspace.project_type.value
                if resolved_target and resolved_target.workspace
                else None
            ),
        )
        results = self._execute(selected, context)
        summary = aggregate(results, context.strict)
        stats = statistics(results)
        capability_fingerprint = self._capability_fingerprint()
        fingerprint = self._fingerprint(
            selected, results, configuration, capability_fingerprint, context.target_identity
        )
        key = f"target:{context.target_identity}" if target_mode else "runtime"
        try:
            previous = self.store.load().snapshots.get(key)
        except Exception:
            if persist:
                raise
            previous = None
        generation_id = f"diagnostics-{fingerprint[:20]}"
        generation = DiagnosticGeneration(
            generation_id=generation_id,
            previous_generation_id=(
                previous.generation.generation_id
                if previous and previous.diagnostic_fingerprint != fingerprint
                else previous.generation.previous_generation_id
                if previous
                else None
            ),
            diagnostic_fingerprint=fingerprint,
            scope=DiagnosticScope.REPOSITORY if target_mode else DiagnosticScope.RUNTIME,
            target_identity=context.target_identity if target_mode else None,
            configuration_fingerprint=configuration.configuration_fingerprint,
            capability_registry_fingerprint=capability_fingerprint,
            total_checks=summary.total_checks,
            healthy_count=summary.healthy_count,
            degraded_count=summary.degraded_count,
            unhealthy_count=summary.unhealthy_count,
            unknown_count=summary.unknown_count,
            not_applicable_count=summary.not_applicable_count,
            skipped_count=summary.skipped_count,
            blocking_count=summary.blocking_count,
            overall_status=summary.overall_status,
        )
        changes = self._changes(previous, results, summary.overall_status)
        snapshot = DiagnosticSnapshot(
            results=results,
            summary=summary,
            statistics=stats,
            diagnostic_fingerprint=fingerprint,
            generation=generation,
            changes=changes,
        )
        if reports:
            self.renderer.write(self.reports_path, snapshot, runtime=not target_mode)
        if persist:
            self.store.save(key, snapshot)
        return DiagnosticResultSet(snapshot=snapshot, persisted=persist, reports_written=reports)

    def _select(
        self,
        definitions: tuple[object, ...],
        target_mode: bool,
        categories: tuple[DiagnosticCategory, ...],
        check_id: str | None,
    ) -> tuple[object, ...]:
        from forge.diagnostics.models import DiagnosticDefinition

        typed = tuple(item for item in definitions if isinstance(item, DiagnosticDefinition))
        scope_selected = tuple(item for item in typed if item.target_required is target_mode)
        if check_id:
            requested = DIAGNOSTIC_REGISTRY.get_check(check_id)
            if requested.target_required is not target_mode:
                return ()
            required: set[str] = set()

            def add(item: DiagnosticDefinition) -> None:
                for dependency in item.prerequisite_checks:
                    add(DIAGNOSTIC_REGISTRY.get_check(dependency))
                required.add(item.check_id)

            add(requested)
            scope_selected = tuple(item for item in typed if item.check_id in required)
        if categories:
            allowed = set(categories)
            scope_selected = tuple(item for item in scope_selected if item.category in allowed)
        if not self.configuration.include_optional:
            scope_selected = tuple(
                item for item in scope_selected if item.criticality.value != "optional"
            )
        return tuple(sorted(scope_selected, key=lambda item: item.check_id))

    @staticmethod
    def _execute(
        definitions: tuple[object, ...], context: DiagnosticContext
    ) -> tuple[DiagnosticResult, ...]:
        from forge.diagnostics.models import DiagnosticDefinition

        pending = {
            item.check_id: item for item in definitions if isinstance(item, DiagnosticDefinition)
        }
        completed: dict[str, DiagnosticResult] = {}
        while pending:
            progressed = False
            for check_id in sorted(tuple(pending)):
                definition = pending[check_id]
                internal = tuple(
                    x for x in definition.prerequisite_checks if x in pending or x in completed
                )
                if not all(item in completed for item in internal):
                    continue
                failed = tuple(
                    item
                    for item in internal
                    if completed[item].status not in {HealthStatus.HEALTHY, HealthStatus.DEGRADED}
                )
                completed[check_id] = (
                    skipped(definition, failed) if failed else execute(definition, context)
                )
                del pending[check_id]
                progressed = True
            if not progressed:
                break
        return tuple(completed[key] for key in sorted(completed))

    @staticmethod
    def _capability_fingerprint() -> str:
        payload = [item.model_dump(mode="json") for item in built_in_catalogue()]
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    @staticmethod
    def _fingerprint(
        definitions: tuple[object, ...],
        results: tuple[DiagnosticResult, ...],
        configuration: ConfigurationSnapshot,
        capability_fingerprint: str,
        target_identity: str | None,
    ) -> str:
        payload = {
            "schema": SCHEMA_VERSION,
            "catalogue": CATALOGUE_VERSION,
            "target": target_identity,
            "definitions": [
                item.model_dump(mode="json") for item in definitions if hasattr(item, "model_dump")
            ],
            "results": [item.model_dump(mode="json") for item in results],
            "configuration": configuration.configuration_fingerprint,
            "capabilities": capability_fingerprint,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    @staticmethod
    def _changes(
        previous: DiagnosticSnapshot | None,
        results: tuple[DiagnosticResult, ...],
        overall: HealthStatus,
    ) -> DiagnosticChangeSet:
        if previous is None:
            return DiagnosticChangeSet(
                changes=tuple(
                    DiagnosticChange(
                        check_id=item.check_id,
                        change_type=DiagnosticChangeType.UNCHANGED,
                    )
                    for item in results
                )
            )
        old = {item.check_id: item for item in previous.results}
        current = {item.check_id: item for item in results}
        changes: list[DiagnosticChange] = []
        for check_id in sorted(set(old) | set(current)):
            if check_id not in old:
                kind = DiagnosticChangeType.ADDED
            elif check_id not in current:
                kind = DiagnosticChangeType.REMOVED
            elif old[check_id].status != current[check_id].status:
                kind = DiagnosticChangeType.STATUS_CHANGED
            elif old[check_id] == current[check_id]:
                kind = DiagnosticChangeType.UNCHANGED
            elif old[check_id].severity != current[check_id].severity:
                kind = DiagnosticChangeType.SEVERITY_CHANGED
            elif old[check_id].blocking != current[check_id].blocking:
                kind = DiagnosticChangeType.BLOCKING_CHANGED
            elif old[check_id].evidence != current[check_id].evidence:
                kind = DiagnosticChangeType.EVIDENCE_CHANGED
            else:
                kind = DiagnosticChangeType.ACTION_CHANGED
            changes.append(DiagnosticChange(check_id=check_id, change_type=kind))
        return DiagnosticChangeSet(
            changes=tuple(changes),
            overall_status_changed=previous.summary.overall_status != overall,
        )
