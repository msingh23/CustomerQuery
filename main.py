"""CLI entry point; model integration is the next implementation step."""

import json
from typing import Sequence

from cli import parse_arguments


def main(argv: Sequence[str] | None = None) -> int:
    request = parse_arguments(argv)
    print(json.dumps({
        'user_id': request.user_id,
        'query': request.query,
        'invoices': None,
        'failure': 'LLM integration is not configured; no invoice query was executed.',
    }))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
