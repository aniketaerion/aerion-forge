"""REST route discovery for M4.4 API Domain Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.api.identifiers import (
    api_endpoint_identifier,
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiEndpoint,
    ApiFinding,
    ApiFindingSeverity,
    HttpMethod,
)

_ROUTE_PATTERNS = (
    re.compile(
        r"""@(?:app|router)\.(?P<method>get|post|put|patch|delete|options|head)\(
        \s*["'](?P<path>[^"']+)["']""",
        re.IGNORECASE | re.VERBOSE,
    ),
    re.compile(
        r"""(?:app|router)\.(?P<method>get|post|put|patch|delete|options|head)\(
        \s*["'](?P<path>[^"']+)["']""",
        re.IGNORECASE | re.VERBOSE,
    ),
)


def discover_rest_endpoints(
    project_root: Path,
) -> tuple[ApiEndpoint, ...]:
    """Discover REST endpoints from local source files."""
    endpoints: dict[tuple[str, str], ApiEndpoint] = {}

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".py", ".ts", ".js"}:
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
                "dist",
                "build",
            )
        ):
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        relative = path.relative_to(project_root).as_posix()

        for pattern in _ROUTE_PATTERNS:
            for match in pattern.finditer(source):
                method = HttpMethod(
                    match.group("method").upper()
                )
                route = match.group("path")
                key = (method.value, route)

                endpoints[key] = ApiEndpoint(
                    endpoint_id=api_endpoint_identifier(
                        {
                            "method": method.value,
                            "path": route,
                            "source_path": relative,
                        }
                    ),
                    path=route,
                    method=method,
                    source_path=relative,
                )

    return tuple(
        sorted(
            endpoints.values(),
            key=lambda endpoint: (
                endpoint.path,
                endpoint.method.value,
            ),
        )
    )


def rest_findings(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    """Produce REST discovery findings."""
    endpoints = discover_rest_endpoints(project_root)

    if not endpoints:
        return ()

    finding_id = api_finding_identifier(
        {
            "category": "rest",
            "endpoint_ids": [
                endpoint.endpoint_id
                for endpoint in endpoints
            ],
        }
    )

    return (
        ApiFinding(
            finding_id=finding_id,
            category="rest",
            severity=ApiFindingSeverity.INFO,
            message="REST endpoints detected.",
            evidence={
                "endpoint_count": str(len(endpoints)),
                "paths": ",".join(
                    endpoint.path for endpoint in endpoints
                ),
            },
        ),
    )