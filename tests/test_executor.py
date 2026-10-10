import sqlite3
import unittest
from datetime import date

from db.engine import SQLiteDBEngine
from db.executor import DatabaseExecutor
from db.sample_data import create_sample_database


class DatabaseExecutorTests(unittest.TestCase):
    def setUp(self):
        self.connection = create_sample_database(date(2026, 10, 9))
        self.addCleanup(self.connection.close)
        self.executor = DatabaseExecutor(self.connection)

    def test_invoice_results_and_aggregate(self):
        rows = self.executor.execute(
            "SELECT invoice_id, invoice_amount FROM invoices "
            "WHERE invoice_amount > 10000 ORDER BY invoice_id"
        )
        self.assertEqual(len(rows), 5)
        self.assertEqual(rows[0], {"invoice_id": 101, "invoice_amount": 12000})
        self.assertEqual(
            self.executor.execute(
                "SELECT COUNT(*) AS unpaid_count FROM invoices WHERE invoice_status = 'unpaid'"
            ),
            [{"unpaid_count": 6}],
        )

    def test_join_and_empty_results(self):
        self.assertEqual(
            self.executor.execute(
                "SELECT users.name, SUM(invoice_amount) AS total FROM invoices "
                "JOIN users USING (user_id) GROUP BY users.name ORDER BY users.name"
            ),
            [{"name": "Alice", "total": 78000}, {"name": "Bob", "total": 21700}],
        )
        self.assertEqual(
            self.executor.execute("SELECT * FROM invoices WHERE invoice_id = -1"), []
        )

    def test_errors(self):
        with self.assertRaises(ValueError):
            self.executor.execute(" ")
        with self.assertRaises(sqlite3.OperationalError):
            self.executor.execute("SELECT * FROM unknown_table")
        with self.assertRaises(sqlite3.ProgrammingError):
            self.executor.execute("SELECT 1; SELECT 2;")
        with self.assertRaisesRegex(ValueError, "aliases"):
            self.executor.execute(
                "SELECT users.user_id, invoices.user_id FROM users JOIN invoices USING (user_id)"
            )

    def test_engine_connection_and_caller_owned_transaction(self):
        with SQLiteDBEngine() as engine:
            connection = engine.connect()
            executor = DatabaseExecutor(connection)
            self.assertEqual(
                executor.execute("INSERT INTO users VALUES (1, 'Alice')"), []
            )
            self.assertEqual(
                executor.execute("SELECT name FROM users"), [{"name": "Alice"}]
            )
            connection.rollback()
            self.assertEqual(executor.execute("SELECT * FROM users"), [])


if __name__ == "__main__":
    unittest.main()
