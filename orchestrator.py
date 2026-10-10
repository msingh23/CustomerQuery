"""Connect the natural-language invoice query happy flow."""

import json
from dataclasses import replace
from datetime import datetime
from zoneinfo import ZoneInfo

from db.engine import SQLiteDBEngine
from db.executor import DatabaseExecutor
from llm.client import LLMClient
from llm.llm_query_translator import LLMQueryTranslator
from models.query_response import QueryResponse
from models.response_mapper import InvoiceResponseMapper
from validator.output.sql_query_validator import SQLQueryValidator
from validator.input.query import UserInputValidator
from validator.output.user_query_validator import UserQueryValidator


class QueryOrchestrator:
    def __init__(
        self,
        engine: SQLiteDBEngine,
        translator: LLMQueryTranslator,
        llm_client: LLMClient,
        sql_validator: SQLQueryValidator,
        user_validator: UserQueryValidator,
        input_validator: UserInputValidator | None = None,
        response_mapper: InvoiceResponseMapper | None = None,
    ) -> None:
        self.engine = engine
        self.translator = translator
        self.llm_client = llm_client
        self.sql_validator = sql_validator
        self.user_validator = user_validator
        self.input_validator = input_validator or UserInputValidator()
        self.response_mapper = response_mapper or InvoiceResponseMapper()

    def run(self, user_input: str, user_id: int) -> QueryResponse:
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("User ID must be a positive integer.")
        valid, reason = self.input_validator.validate(user_input)
        if not valid:
            raise ValueError(reason)
        today = datetime.now(ZoneInfo("America/Los_Angeles")).date()
        translator = replace(
            self.translator,
            rules=[
                *self.translator.rules,
                f"The authenticated user ID is {user_id}. Restrict each table alias "
                f"with a mandatory WHERE user_id = {user_id} predicate.",
                f"Today is {today.isoformat()} in America/Los_Angeles.",
            ],
        )
        output = json.loads(
            self.llm_client.generate(translator.build_prompt(user_input))
        )
        if not isinstance(output, dict) or set(output) != {
            "sql_query",
            "reasoning",
            "failure",
        }:
            raise ValueError(
                "LLM response must contain sql_query, reasoning, and failure."
            )
        valid, reason = self.sql_validator.validate_response(output)
        if not valid:
            raise ValueError(reason)
        if not isinstance(output["reasoning"], str) or not output["reasoning"].strip():
            raise ValueError("Successful LLM response requires a concise rationale.")
        valid, reason = self.user_validator.validate(output["sql_query"], user_id)
        if not valid:
            raise ValueError(reason)
        rows = DatabaseExecutor(self.engine.connect()).execute(output["sql_query"])
        return self.response_mapper.map(rows, output["reasoning"])
