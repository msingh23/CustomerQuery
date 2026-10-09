"""Execute SQL against an existing SQLite connection."""

import sqlite3
from typing import Any


class DatabaseExecutor:
    """Execute one statement and return rows keyed by column name.

    The caller owns the connection and any commit/rollback decisions. Validate
    LLM-generated SQL before passing it here; execution does not enforce rules.
    SQLite errors propagate to the caller.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def execute(self, sql_query: str) -> list[dict[str, Any]]:
        if not isinstance(sql_query, str) or not sql_query.strip():
            raise ValueError("SQL query must be a non-empty string.")
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql_query)
            if cursor.description is None:
                return []
            columns = [column[0] for column in cursor.description]
            if len(columns) != len(set(columns)):
                raise ValueError("Result column names must be unique; use SQL aliases.")
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()
