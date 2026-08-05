from forge.domain_intelligence.database.models import (
    DatabaseConstraint,
    DatabaseObjectKind,
    DatabaseTable,
)
from forge.domain_intelligence.database.relationships import (
    relationship_edges,
)


def test_relationship_edges() -> None:
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

    assert relationship_edges((table,)) == (
        (
            "public.orders",
            "public.customers",
            "orders_customer_fkey",
        ),
    )