from pathlib import Path

from forge.domain_intelligence.api.models import HttpMethod
from forge.domain_intelligence.api.rest import (
    discover_rest_endpoints,
)


def test_discover_rest_endpoints(tmp_path: Path) -> None:
    (tmp_path / "routes.py").write_text(
        """
        @router.get("/orders")
        def list_orders():
            return []
        """,
        encoding="utf-8",
    )

    endpoints = discover_rest_endpoints(tmp_path)

    assert len(endpoints) == 1
    assert endpoints[0].path == "/orders"
    assert endpoints[0].method is HttpMethod.GET