from pathlib import Path

from forge.domain_intelligence.api.models import (
    ApiStyle,
    HttpMethod,
)
from forge.domain_intelligence.api.openapi import (
    discover_openapi_files,
    parse_openapi_file,
)


def test_openapi_discovery_and_parsing(
    tmp_path: Path,
) -> None:
    (tmp_path / "openapi.yaml").write_text(
        """
        openapi: 3.0.0
        info:
          title: ERP API
          version: 1.0.0
        paths:
          /orders:
            get:
              operationId: listOrders
              responses:
                "200":
                  description: Success
        """,
        encoding="utf-8",
    )

    assert discover_openapi_files(tmp_path) == (
        "openapi.yaml",
    )

    contract = parse_openapi_file(
        tmp_path,
        "openapi.yaml",
    )

    assert contract.style is ApiStyle.OPENAPI
    assert contract.title == "ERP API"
    assert contract.endpoints[0].method is HttpMethod.GET