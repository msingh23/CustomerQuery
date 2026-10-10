"""Validate generated SQL without executing it."""

from dataclasses import dataclass, field
from typing import Mapping, Sequence

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError


@dataclass(frozen=True)
class SQLValidationRules:
    dialect: str
    allowed_tables: frozenset[str]
    allowed_operations: frozenset[str] = frozenset({"SELECT"})
    allowed_joins: frozenset[str] = frozenset()
    allowed_aggregations: frozenset[str] = frozenset()
    # SQLGlot expression names. Everything outside this list is rejected.
    allowed_constructs: frozenset[str] = field(
        default_factory=lambda: frozenset(
            {
                "Select",
                "From",
                "Table",
                "TableAlias",
                "Identifier",
                "Column",
                "Star",
                "Alias",
                "Literal",
                "Null",
                "Boolean",
                "Where",
                "And",
                "Or",
                "Not",
                "Paren",
                "EQ",
                "NEQ",
                "GT",
                "GTE",
                "LT",
                "LTE",
                "Is",
                "In",
                "Between",
                "Like",
                "Order",
                "Ordered",
                "Limit",
                "Offset",
                "Distinct",
                "Group",
                "Having",
                "Join",
            }
        )
    )


class SQLQueryValidator:
    """Fail closed against a configured allowlist; return (valid, reason).

    This initial version supports a single SELECT, including permitted
    aggregates and join types. CTEs, subqueries, and other statement types
    are deliberately unsupported. Validation does not check column existence,
    join relationships, permissions, or whether query results are correct.
    """

    def __init__(self, rules: SQLValidationRules):
        self.rules = rules
        self.operations = {value.upper() for value in rules.allowed_operations}
        self.joins = {value.upper() for value in rules.allowed_joins}
        self.aggregations = {value.upper() for value in rules.allowed_aggregations}

    def validate(
        self, sql_query: str | None, failure_codes: Sequence[str] = ()
    ) -> tuple[bool, str | None]:
        if failure_codes:
            return False, f"LLM reported failure: {', '.join(failure_codes)}"
        if not isinstance(sql_query, str) or not sql_query.strip():
            return False, "SQL query is missing or empty."
        try:
            statements = [
                node
                for node in sqlglot.parse(sql_query, read=self.rules.dialect)
                if node is not None
            ]
        except (SqlglotError, ValueError) as error:
            return False, f"Unable to parse SQL: {error}"
        if len(statements) != 1:
            return False, "Exactly one SQL statement is allowed."
        query = statements[0]
        if not isinstance(query, exp.Select) or "SELECT" not in self.operations:
            return False, "Only an explicitly allowed SELECT operation is supported."
        if not query.expressions:
            return False, "SELECT must contain at least one projection."
        if sum(isinstance(node, exp.Select) for node in query.walk()) != 1:
            return False, "Subqueries are not supported."
        for node in query.walk():
            if isinstance(node, exp.AggFunc):
                name = node.sql_name().upper()
                if name not in self.aggregations:
                    return False, f"Aggregation is not allowed: {name}"
            elif type(node).__name__ not in self.rules.allowed_constructs:
                return False, f"SQL construct is not allowed: {type(node).__name__}"
            if isinstance(node, exp.Table):
                # Qualification is part of identity; public.invoices is not
                # implicitly authorized by an invoices allowlist entry.
                name = ".".join(part.name for part in node.parts)
                if name not in self.rules.allowed_tables:
                    return False, f"Table is not allowed: {name}"
            if isinstance(node, exp.Join):
                join_type = " ".join(filter(None, (node.side, node.kind))) or "INNER"
                if node.method or join_type not in self.joins:
                    return False, f"Join is not allowed: {node.method or join_type}"
                if join_type != "CROSS" and not (
                    node.args.get("on") or node.args.get("using")
                ):
                    return False, "A non-CROSS join requires ON or USING."
        return True, None

    def validate_response(
        self, output: Mapping[str, object], failure_codes: Sequence[str] = ()
    ) -> tuple[bool, str | None]:
        """Accept the translator's decoded JSON response and external codes."""
        if output.get("failure") is not None:
            return False, f"LLM reported failure: {output['failure']}"
        return self.validate(output.get("sql_query"), failure_codes)
