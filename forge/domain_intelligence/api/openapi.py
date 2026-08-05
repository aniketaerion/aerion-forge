"""OpenAPI discovery and parsing for M4.4."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from forge.domain_intelligence.api.identifiers import (
    api_contract_identifier,
    api_endpoint_identifier,
    api_finding_identifier,
)
from forge.domain_intelligence.api.models import (
    ApiContract,
    ApiEndpoint,
    ApiFinding,
    ApiFindingSeverity,
    ApiResponse,
    ApiStyle,
    HttpMethod,
)

_OPENAPI_NAMES = {
    "openapi.json",
    "openapi.yaml",
    "openapi.yml",
    "swagger.json",
    "swagger.yaml",
    "swagger.yml",
}


def discover_openapi_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover OpenAPI and Swagger contract files."""
    files: set[str] = set()

    for path in project_root.rglob("*"):
        if not path.is_file():
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

        if path.name.lower() in _OPENAPI_NAMES:
            files.add(
                path.relative_to(project_root).as_posix()
            )

    return tuple(sorted(files))


def _load_document(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    else:
        raw = yaml.safe_load(
            path.read_text(encoding="utf-8-sig")
        )

    return raw if isinstance(raw, dict) else {}


def parse_openapi_file(
    project_root: Path,
    relative_path: str,
) -> ApiContract:
    """Parse one local OpenAPI or Swagger contract."""
    path = project_root / relative_path
    document = _load_document(path)

    info = document.get("info")
    info_mapping = info if isinstance(info, dict) else {}

    title = str(info_mapping.get("title") or path.stem)
    version_value = info_mapping.get("version")
    version = (
        str(version_value)
        if version_value is not None
        else None
    )

    endpoints: list[ApiEndpoint] = []
    paths = document.get("paths")
    path_mapping = paths if isinstance(paths, dict) else {}

    for route, operations in path_mapping.items():
        if not isinstance(route, str):
            continue

        if not isinstance(operations, dict):
            continue

        for method_name, operation in operations.items():
            normalized = str(method_name).upper()

            if normalized not in HttpMethod.__members__:
                continue

            method = HttpMethod[normalized]
            operation_mapping = (
                operation
                if isinstance(operation, dict)
                else {}
            )
            responses_raw = operation_mapping.get("responses")
            responses_mapping = (
                responses_raw
                if isinstance(responses_raw, dict)
                else {}
            )

            responses = tuple(
                ApiResponse(
                    status_code=str(status),
                    description=str(
                        value.get("description", "")
                    )
                    if isinstance(value, dict)
                    else "",
                )
                for status, value in sorted(
                    responses_mapping.items(),
                    key=lambda item: str(item[0]),
                )
            )

            endpoints.append(
                ApiEndpoint(
                    endpoint_id=api_endpoint_identifier(
                        {
                            "method": method.value,
                            "path": route,
                            "source_path": relative_path,
                        }
                    ),
                    path=route,
                    method=method,
                    operation_id=(
                        str(operation_mapping["operationId"])
                        if "operationId" in operation_mapping
                        else None
                    ),
                    summary=(
                        str(operation_mapping["summary"])
                        if "summary" in operation_mapping
                        else None
                    ),
                    responses=responses,
                    tags=tuple(
                        str(tag)
                        for tag in operation_mapping.get(
                            "tags",
                            (),
                        )
                        if isinstance(tag, str)
                    ),
                    source_path=relative_path,
                )
            )

    contract_id = api_contract_identifier(
        {
            "title": title,
            "version": version,
            "source_path": relative_path,
            "endpoint_ids": [
                endpoint.endpoint_id
                for endpoint in endpoints
            ],
        }
    )

    return ApiContract(
        contract_id=contract_id,
        title=title,
        version=version,
        style=ApiStyle.OPENAPI,
        source_path=relative_path,
        endpoints=tuple(
            sorted(
                endpoints,
                key=lambda endpoint: (
                    endpoint.path,
                    endpoint.method.value,
                ),
            )
        ),
    )


def openapi_findings(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    """Produce OpenAPI discovery findings."""
    files = discover_openapi_files(project_root)

    if not files:
        return ()

    finding_id = api_finding_identifier(
        {
            "category": "openapi",
            "files": files,
        }
    )

    return (
        ApiFinding(
            finding_id=finding_id,
            category="openapi",
            severity=ApiFindingSeverity.INFO,
            message="OpenAPI contracts detected.",
            evidence={
                "file_count": str(len(files)),
                "files": ",".join(files),
            },
        ),
    )