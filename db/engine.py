"""SQLite connection lifecycle for application data access."""

import sqlite3
from typing import Callable

from db.database import create_database


class SQLiteDBEngine:
    """Own one connection returned by the configured database factory.

    Repeated connect calls reuse the database until close is called.
    Connecting after close calls the factory again to create a fresh database.
    SQL execution is provided separately by DatabaseExecutor.
    """

    def __init__(self, database_factory: Callable[[], sqlite3.Connection] = create_database) -> None:
        self._connection: sqlite3.Connection | None = None
        self._database_factory = database_factory

    def connect(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = self._database_factory()
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
