import pytest

from app.exceptions.api_exceptions import UnsafeSqlError
from app.services.sql_validator import SqlValidator


@pytest.fixture
def validator() -> SqlValidator:
    return SqlValidator()


def test_accepts_simple_select_from_sales(validator: SqlValidator) -> None:
    sql = validator.validate("SELECT product_name FROM sales LIMIT 10", max_rows=50)

    assert sql == "SELECT product_name FROM sales LIMIT 10"


def test_accepts_valid_sales_aggregate_query(validator: SqlValidator) -> None:
    sql = validator.validate(
        """
        SELECT product_name, SUM(quantity) AS total_quantity
        FROM sales
        WHERE week_day = 'Friday'
        GROUP BY product_name
        ORDER BY total_quantity DESC
        LIMIT 5
        """,
        max_rows=50,
    )

    assert "FROM sales" in sql
    assert "SUM(quantity)" in sql


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO sales (product_name) VALUES ('x')",
        "UPDATE sales SET product_name = 'x'",
        "DELETE FROM sales",
        "DROP TABLE sales",
        "CREATE TABLE x (id int)",
    ],
)
def test_rejects_mutating_or_ddl_sql(validator: SqlValidator, sql: str) -> None:
    with pytest.raises(UnsafeSqlError):
        validator.validate(sql, max_rows=50)


def test_rejects_multiple_statements(validator: SqlValidator) -> None:
    with pytest.raises(UnsafeSqlError):
        validator.validate("SELECT * FROM sales; SELECT * FROM users", max_rows=50)


@pytest.mark.parametrize(
    "sql",
    [
        "-- comment\nSELECT * FROM sales",
        "SELECT * FROM sales /* comment */",
    ],
)
def test_rejects_comments(validator: SqlValidator, sql: str) -> None:
    with pytest.raises(UnsafeSqlError):
        validator.validate(sql, max_rows=50)


def test_rejects_unknown_table(validator: SqlValidator) -> None:
    with pytest.raises(UnsafeSqlError):
        validator.validate("SELECT * FROM payment LIMIT 10", max_rows=50)


def test_adds_limit_when_missing(validator: SqlValidator) -> None:
    sql = validator.validate("SELECT product_name FROM sales", max_rows=25)

    assert sql == "SELECT product_name FROM sales LIMIT 25"


def test_caps_limit_above_max_rows(validator: SqlValidator) -> None:
    sql = validator.validate("SELECT product_name FROM sales LIMIT 500", max_rows=50)

    assert sql == "SELECT product_name FROM sales LIMIT 50"


def test_enforces_backend_hard_row_limit(validator: SqlValidator) -> None:
    sql = validator.validate("SELECT product_name FROM sales LIMIT 500", max_rows=500)

    assert sql == "SELECT product_name FROM sales LIMIT 100"


def test_accepts_single_row_aggregate_queries(validator: SqlValidator) -> None:
    sql = validator.validate("SELECT SUM(total) AS total_revenue FROM sales", max_rows=50)

    assert sql == "SELECT SUM(total) AS total_revenue FROM sales LIMIT 50"


def test_rejects_select_without_table_references(validator: SqlValidator) -> None:
    with pytest.raises(UnsafeSqlError):
        validator.validate("SELECT 1", max_rows=50)
