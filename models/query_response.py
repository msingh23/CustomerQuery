"""Happy-flow response containing invoice records and a concise rationale."""

from dataclasses import dataclass

from models.invoice import Invoice


@dataclass(frozen=True)
class QueryResponse:
    invoices: list[Invoice]
    reasoning: str
