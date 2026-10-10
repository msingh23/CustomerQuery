"""Prove explicit user scope for the supported invoice SELECT queries."""

from sqlglot import exp, parse_one

from validator.output.sql_query_validator import SQLQueryValidator, SQLValidationRules


class UserQueryValidator:
    """Require authenticated-user equality in WHERE for every table alias.

    Only invoices and users are supported. Joins require a separate explicit
    scope predicate for each alias. CTEs, subqueries, and set operations are
    rejected. The trusted user ID must come from authentication, not the LLM.
    """

    def __init__(self, dialect: str = "sqlite") -> None:
        self.dialect = dialect
        self.structure = SQLQueryValidator(
            SQLValidationRules(
                dialect=dialect,
                allowed_tables=frozenset({"invoices", "users"}),
                allowed_joins=frozenset({"INNER", "LEFT"}),
                allowed_aggregations=frozenset({"SUM", "COUNT", "AVG", "MIN", "MAX"}),
            )
        )

    @staticmethod
    def _unwrap(node):
        while isinstance(node, exp.Paren):
            node = node.this
        return node

    def validate(
        self, sql_query: str | None, original_user: int
    ) -> tuple[bool, str | None]:
        if type(original_user) is not int:
            return False, "Authenticated user ID must be an integer."
        valid, reason = self.structure.validate(sql_query)
        if not valid:
            return False, reason
        query = parse_one(sql_query, read=self.dialect)
        tables = list(query.find_all(exp.Table))
        if not tables:
            return False, "Query must reference a user-scoped table."
        aliases = [table.alias_or_name for table in tables]
        if len(aliases) != len(set(aliases)):
            return False, "Table references require unique aliases."
        where = query.args.get("where")
        if where is None:
            return False, "WHERE must restrict the query to the authenticated user."

        def column_alias(node):
            if not isinstance(node, exp.Column) or node.name != "user_id":
                return None
            if node.table:
                return node.table if node.table in aliases else None
            return aliases[0] if len(aliases) == 1 else None

        def matches_user(node):
            return (
                isinstance(node, exp.Literal)
                and not node.is_string
                and node.this == str(original_user)
            )

        # Catch explicit references to a different user even in an otherwise
        # scoped query. Column-to-column equality is permitted for joins.
        for equality in query.find_all(exp.EQ):
            left, right = self._unwrap(equality.this), self._unwrap(equality.expression)
            for column, value in ((left, right), (right, left)):
                if isinstance(column, exp.Column) and column.name == "user_id":
                    if column_alias(column) is None:
                        return False, "Ambiguous or unknown user_id table reference."
                    if column_alias(value) is None and not matches_user(value):
                        return (
                            False,
                            "User ID comparison does not match the authenticated user.",
                        )

        def guaranteed_scopes(node):
            node = self._unwrap(node)
            if isinstance(node, exp.And):
                return guaranteed_scopes(node.this) | guaranteed_scopes(node.expression)
            # OR/NOT predicates cannot supply a mandatory user restriction.
            if isinstance(node, exp.EQ):
                left, right = self._unwrap(node.this), self._unwrap(node.expression)
                if matches_user(right) and column_alias(left):
                    return {column_alias(left)}
                if matches_user(left) and column_alias(right):
                    return {column_alias(right)}
            return set()

        missing = set(aliases) - guaranteed_scopes(where.this)
        if missing:
            return False, (
                "Missing mandatory WHERE user_id restriction for: "
                + ", ".join(sorted(missing))
            )
        return True, None
