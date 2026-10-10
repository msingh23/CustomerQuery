import sqlite3
import unittest

from db.engine import SQLiteDBEngine


class SQLiteDBEngineTests(unittest.TestCase):
    def test_reuses_connection_and_reopens_empty(self):
        engine = SQLiteDBEngine()
        self.addCleanup(engine.close)
        connection = engine.connect()
        connection.execute(
            "INSERT INTO users (user_id, name) VALUES (?, ?)", (1, "Alice")
        )
        self.assertIs(engine.connect(), connection)
        self.assertEqual(
            engine.connect().execute("SELECT name FROM users").fetchall(), [("Alice",)]
        )
        engine.close()
        engine.close()
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
        self.assertEqual(engine.connect().execute("SELECT * FROM users").fetchall(), [])

    def test_context_closes_on_error(self):
        with self.assertRaisesRegex(RuntimeError, "example"):
            with SQLiteDBEngine() as engine:
                connection = engine.connect()
                raise RuntimeError("example")
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
