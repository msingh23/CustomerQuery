import contextlib
import io
import json
import unittest
from datetime import date
from unittest.mock import Mock

from application import create_orchestrator
from db.engine import SQLiteDBEngine
from db.sample_data import create_sample_database
from main import main


class TestLLMClient:
    def __init__(self, sql):
        self.sql = sql
        self.prompts = []

    def generate(self, prompt):
        self.prompts.append(prompt)
        return json.dumps({'sql_query': self.sql, 'reasoning': 'Filters invoices for the caller.', 'failure': None})


class OrchestratorTests(unittest.TestCase):
    def test_happy_flow(self):
        client = TestLLMClient('SELECT * FROM invoices WHERE user_id = 1 AND invoice_amount > 10000 ORDER BY invoice_id')
        with SQLiteDBEngine(lambda: create_sample_database(date(2026, 10, 9))) as engine:
            response = create_orchestrator(engine, client).run('show invoices over $10,000', 1)
        self.assertEqual(len(response.invoices), 5)
        self.assertEqual(response.invoices[0].invoice_id, 101)
        self.assertTrue(all(invoice.user_id == 1 for invoice in response.invoices))
        self.assertIn('CREATE TABLE invoices', client.prompts[0])
        self.assertIn('authenticated user ID is 1', client.prompts[0])
        self.assertIn('show invoices over $10,000', client.prompts[0])
        self.assertIn('Only invoices and users', client.prompts[0])

    def test_invalid_input_stops_before_model(self):
        client = Mock()
        engine = Mock()
        with self.assertRaises(ValueError):
            create_orchestrator(engine, client).run('SELECT * FROM invoices', 1)
        client.generate.assert_not_called()
        engine.connect.assert_not_called()

    def test_post_model_validation_stops_execution(self):
        for sql in ('DELETE FROM invoices', 'SELECT * FROM invoices WHERE user_id = 2',
                    'SELECT * FROM invoices WHERE user_id = 1 OR 1 = 1'):
            engine = Mock()
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                create_orchestrator(engine, TestLLMClient(sql)).run('show invoices', 1)
            engine.connect.assert_not_called()

    def test_empty_invoice_response(self):
        with SQLiteDBEngine(create_sample_database) as engine:
            response = create_orchestrator(engine, TestLLMClient(
                'SELECT * FROM invoices WHERE user_id = 2 AND invoice_amount > 10000'
            )).run('show invoices over $10,000', 2)
        self.assertEqual(response.invoices, [])

    def test_cli_calls_orchestrator(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            status = main(['--user-id', '2', '--query', 'show unpaid invoices'],
                          TestLLMClient("SELECT * FROM invoices WHERE user_id = 2 AND invoice_status = 'unpaid'"))
        self.assertEqual(status, 0)
        response = json.loads(output.getvalue())
        self.assertEqual(len(response['invoices']), 3)
        self.assertTrue(all(invoice['user_id'] == 2 for invoice in response['invoices']))


if __name__ == '__main__':
    unittest.main()
