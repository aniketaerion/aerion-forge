from forge.domain_intelligence.database.indexes import extract_indexes


def test_extract_indexes() -> None:
    indexes = extract_indexes(
        """
        CREATE UNIQUE INDEX orders_reference_idx
        ON public.orders USING btree (reference);
        """
    )

    assert len(indexes) == 1
    assert indexes[0].name == "orders_reference_idx"
    assert indexes[0].unique
    assert indexes[0].method == "btree"