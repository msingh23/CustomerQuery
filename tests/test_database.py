import sqlite3
import unittest

from db.database import create_database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.connection = create_database()
        self.addCleanup(self.connection.close)

    def test_schema_starts_empty(self):
        expected = {
            'users': ['user_id', 'name'],
            'invoices': ['invoice_id', 'invoice_amount', 'invoice_date',
                         'invoice_status', 'user_id'],
        }
        for table, columns in expected.items():
            actual = self.connection.execute(f'PRAGMA table_info({table})').fetchall()
            self.assertEqual([column[1] for column in actual], columns)
            self.assertEqual(self.connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone(), (0,))

    def test_invoice_requires_existing_user(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                'INSERT INTO invoices VALUES (?, ?, ?, ?, ?)',
                (1, 100, '2026-01-01', 'unpaid', 1),
            )
        self.connection.execute('INSERT INTO users (user_id) VALUES (?)', (1,))
        self.connection.execute(
            'INSERT INTO invoices VALUES (?, ?, ?, ?, ?)',
            (1, 100, '2026-01-01', 'unpaid', 1),
        )
        self.assertEqual(self.connection.execute(
            'SELECT invoice_id FROM invoices JOIN users USING (user_id)'
        ).fetchall(), [(1,)])

    def test_invoice_status_constraint(self):
        self.connection.execute('INSERT INTO users (user_id) VALUES (?)', (1,))
        for invoice_id, status in enumerate(('paid', 'unpaid'), start=1):
            self.connection.execute(
                'INSERT INTO invoices VALUES (?, ?, ?, ?, ?)',
                (invoice_id, 100, '2026-01-01', status, 1),
            )
        for status in ('pending', 'PAID', '', None):
            with self.subTest(status=status):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.connection.execute(
                        'INSERT INTO invoices VALUES (?, ?, ?, ?, ?)',
                        (3, 100, '2026-01-01', status, 1),
                    )
        with self.assertRaises(sqlite3.IntegrityError):
            self.connection.execute(
                'UPDATE invoices SET invoice_status = ? WHERE invoice_id = ?',
                ('pending', 1),
            )

    def test_databases_are_isolated(self):
        self.connection.execute('INSERT INTO users (user_id) VALUES (?)', (1,))
        other = create_database()
        self.addCleanup(other.close)
        self.assertEqual(other.execute('SELECT COUNT(*) FROM users').fetchone(), (0,))


if __name__ == '__main__':
    unittest.main()
