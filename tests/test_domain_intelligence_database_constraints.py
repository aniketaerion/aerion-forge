from forge.domain_intelligence.database.constraints import (
    extract_constraints,
)
from forge.domain_intelligence.database.models import DatabaseObjectKind


def test_extract_constraints() -> None:
    constraints = extract_constraints(
        """
        CONSTRAINT orders_pkey PRIMARY KEY (id),
        CONSTRAINT orders_customer_fkey
            FOREIGN KEY (customer_id)
            REFERENCES public.customers(id),
        UNIQUE (reference)
        """,
        schema_name="public",
        table_name="orders",
    )

    assert {
        constraint.kind for constraint in constraints
    } == {
        DatabaseObjectKind.PRIMARY_KEY,
        DatabaseObjectKind.FOREIGN_KEY,
        DatabaseObjectKind.UNIQUE_CONSTRAINT,
    }