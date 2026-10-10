"""Heuristic screening for direct SQL in natural-language input."""

import re
from typing import Sequence


SQL_KEYWORDS = (
    'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'CREATE',
    'TRUNCATE', 'UNION', 'PRAGMA', 'ATTACH', 'DETACH', 'REPLACE',
    'EXEC', 'EXECUTE', 'GRANT', 'REVOKE',
)
SQL_CONSTRUCTS = (
    r'\bGROUP\s+BY\b', r'\bORDER\s+BY\b',
    r'\b(?:INNER|LEFT|RIGHT|CROSS|NATURAL)\s+JOIN\b',
    r'\bWHERE\s+[\w.]+\s*(?:=|<>|!=|<=|>=|<|>)',
    r'\b(?:FROM|JOIN)\s+(?:invoices|users)\b',
    r'--', r'/\*', r'\*/', r';',
)


class UserInputValidator:
    """Return (valid, reason); this heuristic is not a SQL security boundary.

    Keywords match whole words, case-insensitively. Some ordinary requests
    containing words such as 'update' will be rejected by this simple policy.
    SQL validation and authenticated user scoping remain separate checks.
    """

    def __init__(self, keywords: Sequence[str] = SQL_KEYWORDS) -> None:
        self.keyword_pattern = re.compile(
            r'\b(?:' + '|'.join(re.escape(word) for word in keywords) + r')\b',
            re.IGNORECASE,
        ) if keywords else None
        self.construct_pattern = re.compile('|'.join(SQL_CONSTRUCTS), re.IGNORECASE)

    def validate(self, query: str) -> tuple[bool, str | None]:
        if not isinstance(query, str) or not query.strip():
            return False, 'Natural-language query must not be empty.'
        for pattern in (self.keyword_pattern, self.construct_pattern):
            match = pattern.search(query) if pattern else None
            if match:
                return False, f'SQL keyword or database construct is not allowed: {match.group()}'
        return True, None
