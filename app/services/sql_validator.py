import re

import sqlglot
from sqlglot import exp

from app.exceptions.api_exceptions import UnsafeSqlError
from app.prompts.sales_schema import ALLOWED_SALES_TABLES


COMMENT_PATTERNS = ("--", "/*", "*/")
BACKEND_MAX_ROWS = 100
FORBIDDEN_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Grant,
    exp.Revoke,
    exp.Merge,
    exp.Execute,
    exp.Copy,
    exp.Command,
)


class SqlValidator:
    def __init__(self, allowed_tables: set[str] | None = None) -> None:
        self.allowed_tables = allowed_tables or ALLOWED_SALES_TABLES

    def validate(self, sql: str, max_rows: int) -> str:
        effective_max_rows = min(max_rows, BACKEND_MAX_ROWS)
        if not sql or not sql.strip():
            raise UnsafeSqlError("SQL is required for query decisions.")

        cleaned_sql = self._strip_optional_trailing_semicolon(sql.strip())
        self._reject_comments(cleaned_sql)
        self._reject_semicolon_chaining(cleaned_sql)

        try:
            statements = sqlglot.parse(cleaned_sql, read="postgres")
        except sqlglot.errors.ParseError as exc:
            raise UnsafeSqlError("SQL could not be parsed as PostgreSQL.") from exc

        statements = [statement for statement in statements if statement is not None]
        if len(statements) != 1:
            raise UnsafeSqlError("SQL must contain exactly one statement.")

        expression = statements[0]
        self._reject_non_select(expression)
        self._reject_forbidden_nodes(expression)
        self._validate_tables(expression)
        self._enforce_limit(expression, effective_max_rows)

        return expression.sql(dialect="postgres")

    def _strip_optional_trailing_semicolon(self, sql: str) -> str:
        return re.sub(r";\s*$", "", sql, count=1).strip()

    def _reject_comments(self, sql: str) -> None:
        if any(pattern in sql for pattern in COMMENT_PATTERNS):
            raise UnsafeSqlError("SQL comments are not allowed.")

    def _reject_semicolon_chaining(self, sql: str) -> None:
        if ";" in sql:
            raise UnsafeSqlError("Multiple SQL statements are not allowed.")

    def _reject_non_select(self, expression: exp.Expression) -> None:
        if isinstance(expression, exp.Select):
            return
        if isinstance(expression, (exp.Union, exp.Except, exp.Intersect)) and all(
            isinstance(node, exp.Select) for node in expression.find_all(exp.Select)
        ):
            return
        raise UnsafeSqlError("Only SELECT queries are allowed.")

    def _reject_forbidden_nodes(self, expression: exp.Expression) -> None:
        if any(expression.find(forbidden) is not None for forbidden in FORBIDDEN_EXPRESSIONS):
            raise UnsafeSqlError("SQL contains a forbidden operation.")

        if expression.find(exp.Lock) is not None:
            raise UnsafeSqlError("SELECT locking clauses are not allowed.")

    def _validate_tables(self, expression: exp.Expression) -> None:
        tables = list(expression.find_all(exp.Table))
        if not tables:
            raise UnsafeSqlError("SELECT queries must reference allowed sales tables.")

        for table in tables:
            if table.db and table.db.lower() not in {"public"}:
                raise UnsafeSqlError("Only public sales tables are allowed.")

            table_name = table.name.lower()
            if table_name not in self.allowed_tables:
                raise UnsafeSqlError(f"Table '{table.name}' is not allowed.")

    def _enforce_limit(self, expression: exp.Expression, max_rows: int) -> None:
        limit = expression.args.get("limit")
        if limit is None:
            expression.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))
            return

        limit_value = self._extract_limit_value(limit)
        if limit_value is None:
            raise UnsafeSqlError("LIMIT must be a numeric literal.")

        if limit_value > max_rows:
            expression.set("limit", exp.Limit(expression=exp.Literal.number(max_rows)))

    def _extract_limit_value(self, limit: exp.Limit) -> int | None:
        expression = limit.expression
        if not isinstance(expression, exp.Literal) or not expression.is_int:
            return None

        try:
            return int(expression.this)
        except (TypeError, ValueError):
            return None
