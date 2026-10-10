"""Invoice response data object matching the database schema."""

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Invoice:
    invoice_id: int
    invoice_amount: int | float
    invoice_date: str
    invoice_status: str
    user_id: int

    @classmethod
    def from_row(cls, row: Mapping[str, object]) -> "Invoice":
        """Map a full invoice result row; missing fields raise KeyError."""
        return cls(**{name: row[name] for name in cls.__dataclass_fields__})
