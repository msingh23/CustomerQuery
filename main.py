"""Parse arguments and invoke the invoice query orchestrator."""

import json
from dataclasses import asdict
from typing import Sequence

from cli import parse_arguments
from application import create_orchestrator
from db.engine import SQLiteDBEngine
from db.sample_data import create_sample_database
from llm.client import LLMClient


def main(argv: Sequence[str] | None = None, llm_client: LLMClient | None = None) -> int:
    request = parse_arguments(argv)
    try:
        with SQLiteDBEngine(database_factory=create_sample_database) as engine:
            response = create_orchestrator(engine, llm_client).run(request.query, request.user_id)
        print(json.dumps(asdict(response)))
        return 0
    except (ValueError, RuntimeError) as error:
        failure = str(error)
    print(json.dumps({
        'user_id': request.user_id,
        'query': request.query,
        'invoices': None,
        'failure': failure,
    }))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
