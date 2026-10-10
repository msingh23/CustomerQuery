"""Create a fresh in-memory database populated with Alice and Bob invoices."""

import calendar
import sqlite3
from datetime import date, datetime
from zoneinfo import ZoneInfo

from db.database import create_database


def months_ago(day: date, months: int) -> date:
    """Shift calendar months, clamping the day for shorter months."""
    year, month_index = divmod(day.year * 12 + day.month - 1 - months, 12)
    month = month_index + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def create_sample_database(as_of: date | None = None) -> sqlite3.Connection:
    """Return a populated connection; dates default to today in Los Angeles.

    Each call creates a separate database. The caller owns the connection.
    Amounts are whole USD dollars. Paid/unpaid describes invoice status;
    invoice_date is not a payment date.
    """
    as_of = as_of or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    offsets = (0, 1, 1, 2, 3)
    statuses = ("unpaid", "paid", "unpaid", "paid", "unpaid")
    amounts = {1: (12000, 15000, 18000, 22000, 11000), 2: (500, 1200, 2500, 8000, 9500)}
    invoices = [
        (
            user_id * 100 + index,
            amount,
            months_ago(as_of, offset).isoformat(),
            status,
            user_id,
        )
        for user_id, user_amounts in amounts.items()
        for index, (amount, offset, status) in enumerate(
            zip(user_amounts, offsets, statuses), start=1
        )
    ]
    connection = create_database()
    try:
        with connection:
            connection.executemany(
                "INSERT INTO users (user_id, name) VALUES (?, ?)",
                [(1, "Alice"), (2, "Bob")],
            )
            connection.executemany(
                "INSERT INTO invoices "
                "(invoice_id, invoice_amount, invoice_date, invoice_status, user_id) "
                "VALUES (?, ?, ?, ?, ?)",
                invoices,
            )
    except Exception:
        connection.close()
        raise
    return connection


if __name__ == "__main__":
    connection = create_sample_database()
    try:
        for row in connection.execute(
            "SELECT users.name, invoices.* FROM invoices "
            "JOIN users USING (user_id) ORDER BY invoice_id"
        ):
            print(row)
    finally:
        connection.close()
