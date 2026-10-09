"""SQLite connection lifecycle scaffold for future data access."""

import sqlite3

from db.database import create_database


class SQLiteDBEngine:
    """Own one in-memory connection with the invoice schema.

    Repeated connect calls reuse the database until close is called.
    Connecting after close creates a fresh, empty database. Query execution
    and data-access methods will be added in the next implementation step.
    """

    def __init__(self) -> None:
        self._connection: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = create_database()
        return self._connection

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "SQLiteDBEngine":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
