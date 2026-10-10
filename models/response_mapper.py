"""Map database result rows into invoice response objects."""

from typing import Mapping, Sequence

from models.invoice import Invoice
from models.query_response import QueryResponse


class InvoiceResponseMapper:
    def map(
        self, rows: Sequence[Mapping[str, object]], reasoning: str
    ) -> QueryResponse:
        return QueryResponse([Invoice.from_row(row) for row in rows], reasoning)
