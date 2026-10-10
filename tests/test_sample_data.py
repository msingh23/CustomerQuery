import unittest
from datetime import date

from db.sample_data import create_sample_database, months_ago


class SampleDataTests(unittest.TestCase):
    def test_records_and_example_queries(self):
        connection = create_sample_database(date(2026, 10, 9))
        self.addCleanup(connection.close)
        self.assertEqual(
            connection.execute("SELECT * FROM users").fetchall(),
            [(1, "Alice"), (2, "Bob")],
        )
        for user_id in (1, 2):
            rows = connection.execute(
                "SELECT invoice_amount, invoice_status, invoice_date FROM invoices WHERE user_id = ?",
                (user_id,),
            ).fetchall()
            self.assertEqual(len(rows), 5)
            self.assertEqual({row[1] for row in rows}, {"paid", "unpaid"})
            self.assertEqual(min(row[2] for row in rows), "2026-07-09")
            self.assertEqual(max(row[2] for row in rows), "2026-10-09")
            self.assertTrue(
                all(
                    (row[0] > 10000 if user_id == 1 else row[0] < 10000) for row in rows
                )
            )
        self.assertEqual(
            connection.execute(
                "SELECT COUNT(*) FROM invoices WHERE invoice_amount > 10000"
            ).fetchone(),
            (5,),
        )
        self.assertEqual(
            connection.execute(
                "SELECT COUNT(*) FROM invoices WHERE invoice_status = 'unpaid'"
            ).fetchone(),
            (6,),
        )
        self.assertEqual(
            connection.execute(
                "SELECT user_id, SUM(invoice_amount) FROM invoices "
                "WHERE invoice_date >= '2026-09-01' AND invoice_date < '2026-10-01' "
                "GROUP BY user_id ORDER BY user_id"
            ).fetchall(),
            [(1, 33000), (2, 3700)],
        )

    def test_calendar_boundaries(self):
        self.assertEqual(months_ago(date(2024, 3, 31), 1), date(2024, 2, 29))
        self.assertEqual(months_ago(date(2026, 1, 9), 3), date(2025, 10, 9))


if __name__ == "__main__":
    unittest.main()
