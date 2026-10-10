import unittest
from datetime import date

from db.executor import DatabaseExecutor
from db.sample_data import create_sample_database
from validator.output.user_query_validator import UserQueryValidator


class UserQueryValidatorTests(unittest.TestCase):
    def setUp(self):
        self.validator = UserQueryValidator()

    def test_valid_scopes(self):
        for sql in (
            "SELECT * FROM invoices WHERE user_id = 1",
            "SELECT COUNT(*) FROM invoices i WHERE (1 = i.user_id) AND invoice_amount > 10000",
            "SELECT * FROM invoices WHERE user_id = 1 AND (invoice_status = 'paid' OR invoice_amount > 10000)",
            "SELECT i.invoice_id, u.name FROM invoices i JOIN users u ON i.user_id = u.user_id WHERE i.user_id = 1 AND u.user_id = 1",
        ):
            with self.subTest(sql=sql):
                self.assertEqual(self.validator.validate(sql, 1), (True, None))

    def test_rejects_scope_bypasses(self):
        for sql in (
            "SELECT * FROM invoices",
            "SELECT * FROM invoices WHERE user_id = 2",
            "SELECT * FROM invoices WHERE user_id = 1 OR 1 = 1",
            "SELECT * FROM invoices WHERE NOT (user_id = 1)",
            "SELECT * FROM invoices WHERE user_id IN (1, 2)",
            "SELECT * FROM invoices WHERE user_id = 1 AND user_id = 2",
            "SELECT * FROM invoices WHERE user_id = 1 OR user_id = 2",
            "SELECT * FROM invoices WHERE user_id = 1 UNION SELECT * FROM invoices",
            "SELECT * FROM invoices WHERE user_id = 1 AND EXISTS (SELECT * FROM users)",
            "SELECT * FROM users u JOIN invoices i ON u.user_id = i.user_id WHERE u.user_id = 1",
            "SELECT * FROM users u JOIN invoices i ON u.user_id = i.user_id WHERE user_id = 1",
            "SELECT * FROM invoices i JOIN invoices j ON i.user_id = j.user_id WHERE i.user_id = 1",
            "SELECT * FROM invoices WHERE user_id = 1; SELECT * FROM users",
            "SELECT * FROM secrets WHERE user_id = 1",
            "SELECT 1 WHERE user_id = 1",
            "",
        ):
            with self.subTest(sql=sql):
                valid, reason = self.validator.validate(sql, 1)
                self.assertFalse(valid)
                self.assertTrue(reason)
        self.assertFalse(
            self.validator.validate("SELECT * FROM invoices WHERE user_id = 1", True)[0]
        )

    def test_execution_returns_only_callers_rows(self):
        connection = create_sample_database(date(2026, 10, 9))
        self.addCleanup(connection.close)
        executor = DatabaseExecutor(connection)
        for user_id in (1, 2):
            sql = f"SELECT * FROM invoices WHERE user_id = {user_id}"
            self.assertEqual(self.validator.validate(sql, user_id), (True, None))
            rows = executor.execute(sql)
            self.assertEqual(len(rows), 5)
            self.assertTrue(all(row["user_id"] == user_id for row in rows))


if __name__ == "__main__":
    unittest.main()
