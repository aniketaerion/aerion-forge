from forge.domain_intelligence.database.models import (
    DatabaseConstraint,
    DatabaseObjectKind,
    DatabaseTable,
)
from forge.domain_intelligence.database.risk import (
    database_risk_findings,
)


def test_database_risk_findings() -> None:
    table = DatabaseTable(
        table_id="table-orders",
        schema_name="public",
        name="orders",
        constraints=(
            DatabaseConstraint(
                constraint_id="constraint-1",
                name="orders_customer_fkey",
                kind=DatabaseObjectKind.FOREIGN_KEY,
                columns=("customer_id",),
                referenced_schema="public",
                referenced_table="customers",
                referenced_columns=("id",),
            ),
        ),
    )

    categories = {
        finding.category
        for finding in database_risk_findings((table,))
    }

    assert categories == {
        "missing_primary_key",
        "unindexed_foreign_key",
    }