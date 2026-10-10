"""Configure the invoice-query application with an injectable model client."""

from db.database import SCHEMA
from db.engine import SQLiteDBEngine
from llm.client import LLMClient, UnconfiguredLLMClient
from llm.llm_query_translator import LLMQueryTranslator
from orchestrator import QueryOrchestrator
from validator.sql_query_validator import SQLQueryValidator, SQLValidationRules
from validator.user_query_validator import UserQueryValidator


def create_orchestrator(engine: SQLiteDBEngine, llm_client: LLMClient | None = None) -> QueryOrchestrator:
    rules = SQLValidationRules(
        dialect='sqlite', allowed_tables=frozenset({'invoices', 'users'}),
        allowed_joins=frozenset({'INNER', 'LEFT'}),
    )
    translator = LLMQueryTranslator(
        sql_dialect='sqlite', table_context=SCHEMA,
        rules=[
            'Generate exactly one read-only SELECT statement.',
            'Only invoices and users tables are allowed; only INNER and LEFT joins are allowed.',
            'Use no subqueries, CTEs, set operations, functions, or aggregations.',
            'Return all five invoice fields: invoice_id, invoice_amount, invoice_date, invoice_status, user_id.',
            'Return invoice rows, not aggregate answers. Explain an unsupported request with failure.',
            'Invoice statuses are paid and unpaid. Invoice amounts are USD dollars.',
        ],
    )
    return QueryOrchestrator(engine, translator, llm_client or UnconfiguredLLMClient(),
                             SQLQueryValidator(rules), UserQueryValidator())
