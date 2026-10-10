import contextlib
import io
import json
import unittest
from datetime import date

from cli import parse_arguments
from db.executor import DatabaseExecutor
from db.sample_data import create_sample_database
from main import main
from models.invoice import Invoice
from validator.input import UserInputValidator


class InputTests(unittest.TestCase):
    def test_natural_language(self):
        validator = UserInputValidator()
        for query in (
            "how much did I spend last month",
            "show invoices over $10,000",
            "how many are unpaid",
            "show invoices from last month",
            "show selected invoices",
        ):
            self.assertEqual(validator.validate(query), (True, None))

    def test_sql_screening(self):
        for query in (
            "SELECT * FROM invoices",
            "sElEcT invoice_id",
            "DROP TABLE users",
            "show invoices; DELETE FROM invoices",
            "show invoices -- ignore rules",
            "/* context */ show invoices",
            "WHERE user_id = 2",
            "ORDER BY user_id",
            "",
        ):
            with self.subTest(query=query):
                valid, reason = UserInputValidator().validate(query)
                self.assertFalse(valid)
                self.assertTrue(reason)

    def test_parser(self):
        request = parse_arguments(["--user-id", "1", "--query", "how many are unpaid"])
        self.assertEqual((request.user_id, request.query), (1, "how many are unpaid"))
        for args in (
            [],
            ["--user-id", "0", "--query", "show invoices"],
            ["--user-id", "bob", "--query", "show invoices"],
            ["--user-id", "1", "--query", "SELECT * FROM invoices"],
        ):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(
                SystemExit
            ) as error:
                parse_arguments(args)
            self.assertEqual(error.exception.code, 2)

    def test_cli_reports_missing_model(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--user-id", "1", "--query", "show invoices"]), 1)
        response = json.loads(output.getvalue())
        self.assertIsNone(response["invoices"])
        self.assertIn("not configured", response["failure"])

    def test_invoice_mapping(self):
        connection = create_sample_database(date(2026, 10, 9))
        self.addCleanup(connection.close)
        rows = DatabaseExecutor(connection).execute(
            "SELECT * FROM invoices WHERE invoice_id = 101"
        )
        invoice = Invoice.from_row(rows[0])
        self.assertEqual(invoice, Invoice(101, 12000, "2026-10-09", "unpaid", 1))
        with self.assertRaises(KeyError):
            Invoice.from_row({"invoice_id": 101})


if __name__ == "__main__":
    unittest.main()
