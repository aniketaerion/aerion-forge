from forge.domain_intelligence.database.schema import parse_schema_sql


def test_parse_schema_sql() -> None:
    tables = parse_schema_sql(
        """
        CREATE TABLE public.orders (
            id uuid NOT NULL,
            reference text,
            created_at timestamp DEFAULT now()
        );
        """
    )

    assert len(tables) == 1
    assert tables[0].name == "orders"
    assert [column.name for column in tables[0].columns] == [
        "id",
        "reference",
        "created_at",
    ]
    assert not tables[0].columns[0].nullable