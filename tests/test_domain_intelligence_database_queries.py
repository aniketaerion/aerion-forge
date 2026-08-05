from forge.domain_intelligence.database.queries import classify_queries


def test_classify_queries() -> None:
    result = classify_queries(
        """
        SELECT * FROM orders;
        INSERT INTO orders(id) VALUES ('1');
        UPDATE orders SET id = '2';
        DELETE FROM orders WHERE id = '2';
        """
    )

    assert result == {
        "delete": 1,
        "insert": 1,
        "select": 1,
        "update": 1,
    }