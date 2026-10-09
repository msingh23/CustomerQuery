import unittest

from sql_query_validator import SQLQueryValidator, SQLValidationRules


class SQLQueryValidatorTests(unittest.TestCase):
    def setUp(self):
        self.validator = SQLQueryValidator(SQLValidationRules(
            dialect='postgres', allowed_tables=frozenset({'invoices', 'users'}),
            allowed_joins=frozenset({'INNER', 'LEFT'}),
            allowed_aggregations=frozenset({'SUM', 'COUNT'}),
        ))

    def test_allowed_queries(self):
        for sql in (
            'SELECT invoice_id FROM invoices WHERE invoice_amount > 10',
            'SELECT SUM(invoice_amount) FROM invoices',
            'SELECT COUNT(*) FROM invoices',
            'SELECT i.invoice_id FROM invoices AS i LEFT JOIN users AS u ON i.user_id = u.user_id',
            "SELECT 'DROP TABLE users' FROM invoices",
        ):
            with self.subTest(sql=sql):
                self.assertEqual(self.validator.validate(sql), (True, None))

    def test_rejected_queries(self):
        for sql in (
            '', 'SELECT * FROM secrets', 'SELECT * FROM public.invoices',
            'DELETE FROM invoices', 'SELECT * FROM invoices; DROP TABLE users',
            'SELECT AVG(invoice_amount) FROM invoices',
            'SELECT * FROM invoices CROSS JOIN users',
            'SELECT * FROM invoices NATURAL JOIN users',
            'SELECT * FROM invoices JOIN users',
            'SELECT * FROM (SELECT * FROM invoices) AS i',
            'WITH x AS (DELETE FROM invoices RETURNING *) SELECT * FROM x',
            'SELECT pg_sleep(10)', 'SELECT * INTO backup FROM invoices',
            'SELECT * FROM invoices FOR UPDATE', 'SELECT FROM',
        ):
            with self.subTest(sql=sql):
                valid, reason = self.validator.validate(sql)
                self.assertFalse(valid)
                self.assertTrue(reason)

    def test_injected_rules_and_failures(self):
        strict = SQLQueryValidator(SQLValidationRules('postgres', frozenset({'invoices'})))
        self.assertFalse(strict.validate('SELECT COUNT(*) FROM invoices')[0])
        self.assertFalse(strict.validate('SELECT * FROM invoices', ['RULE_VIOLATION'])[0])
        self.assertFalse(strict.validate_response({'sql_query': None, 'failure': 'Ambiguous request'})[0])
        self.assertEqual(strict.validate_response({'sql_query': 'SELECT * FROM invoices', 'failure': None}), (True, None))
        disabled = SQLQueryValidator(SQLValidationRules('postgres', frozenset({'invoices'}), allowed_operations=frozenset()))
        self.assertFalse(disabled.validate('SELECT * FROM invoices')[0])


if __name__ == '__main__':
    unittest.main()
