"""Create an empty invoice database in memory using Python's SQLite support."""

import sqlite3


SCHEMA = """
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY
);

CREATE TABLE invoices (
    invoice_id INTEGER PRIMARY KEY,
    invoice_amount NUMERIC NOT NULL,
    invoice_date TEXT NOT NULL,
    invoice_status TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);
"""


def create_database() -> sqlite3.Connection:
    """Return a new, empty database; the caller must close the connection.

    Dates should be supplied as ISO dates (YYYY-MM-DD). Invoice statuses are
    unrestricted until their permitted values are defined. User details can
    be added when their fields are specified. SQLite NUMERIC affinity does
    not guarantee exact decimal storage for monetary amounts.
    """
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA)
    except Exception:
        connection.close()
        raise
    return connection
