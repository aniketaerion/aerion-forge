"""GraphQL discovery for M4.4 API Domain Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

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
    ApiStyle,
    HttpMethod,
)

_GRAPHQL_TYPE_PATTERN = re.compile(
    r"\btype\s+(Query|Mutation|Subscription)\s*\{",
    re.IGNORECASE,
)


def discover_graphql_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover GraphQL schema and resolver files."""
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

        if path.suffix.lower() in {".graphql", ".gql"}:
            files.add(path.relative_to(project_root).as_posix())
            continue

        if path.suffix.lower() not in {".py", ".ts", ".js"}:
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        lowered = source.lower()

        if any(
            marker in lowered
            for marker in (
                "graphql",
                "resolver",
                "typegraphql",
                "strawberry",
                "graphene",
            )
        ):
            files.add(path.relative_to(project_root).as_posix())

    return tuple(sorted(files))


def parse_graphql_contract(
    project_root: Path,
) -> ApiContract | None:
    """Build one local GraphQL contract from discovered schema files."""
    files = discover_graphql_files(project_root)
    schema_files = tuple(
        relative
        for relative in files
        if Path(relative).suffix.lower() in {".graphql", ".gql"}
    )

    if not schema_files:
        return None

    operations: set[str] = set()

    for relative in schema_files:
        try:
            source = (project_root / relative).read_text(
                encoding="utf-8-sig"
            )
        except OSError:
            continue

        operations.update(
            match.group(1).lower()
            for match in _GRAPHQL_TYPE_PATTERN.finditer(source)
        )

    endpoints = tuple(
        ApiEndpoint(
            endpoint_id=api_endpoint_identifier(
                {
                    "style": "graphql",
                    "operation": operation,
                    "path": "/graphql",
                }
            ),
            path="/graphql",
            method=HttpMethod.POST,
            operation_id=operation,
            tags=("graphql", operation),
            source_path=",".join(schema_files),
        )
        for operation in sorted(operations)
    )

    return ApiContract(
        contract_id=api_contract_identifier(
            {
                "style": "graphql",
                "schema_files": schema_files,
                "operations": sorted(operations),
            }
        ),
        title="Discovered GraphQL API",
        style=ApiStyle.GRAPHQL,
        source_path=",".join(schema_files),
        endpoints=endpoints,
    )


def graphql_findings(
    project_root: Path,
) -> tuple[ApiFinding, ...]:
    """Produce GraphQL discovery findings."""
    files = discover_graphql_files(project_root)

    if not files:
        return ()

    finding_id = api_finding_identifier(
        {
            "category": "graphql",
            "files": files,
        }
    )

    return (
        ApiFinding(
            finding_id=finding_id,
            category="graphql",
            severity=ApiFindingSeverity.INFO,
            message="GraphQL artifacts detected.",
            evidence={
                "file_count": str(len(files)),
                "files": ",".join(files),
            },
        ),
    )