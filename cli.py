"""Parse and validate the caller's user ID and natural-language query."""

import argparse
from dataclasses import dataclass
from typing import Sequence

from validator.input.query import UserInputValidator


@dataclass(frozen=True)
class QueryRequest:
    user_id: int
    query: str


def positive_user_id(value: str) -> int:
    try:
        user_id = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            "User ID must be a positive integer."
        ) from None
    if user_id <= 0:
        raise argparse.ArgumentTypeError("User ID must be a positive integer.")
    return user_id


def parse_arguments(argv: Sequence[str] | None = None) -> QueryRequest:
    parser = argparse.ArgumentParser(
        description="Query invoices using natural language."
    )
    parser.add_argument("--user-id", required=True, type=positive_user_id)
    parser.add_argument(
        "--query", required=True, help="Natural-language invoice question"
    )
    args = parser.parse_args(argv)
    valid, reason = UserInputValidator().validate(args.query)
    if not valid:
        parser.error(reason)
    return QueryRequest(user_id=args.user_id, query=args.query.strip())
