from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_serializer, field_validator


class CertType(StrEnum):
    RAW = "raw"
    CGC = "cgc"


class ComicComp(BaseModel):
    id: str = Field(..., description="Stable comparable sale identifier.")
    title: str
    issue_number: str
    grade: str
    sale_price: Decimal = Field(..., ge=0)
    sale_date: date
    source: str
    url: str | None = None

    @field_serializer("sale_price")
    def serialize_sale_price(self, value: Decimal) -> float:
        return float(value)


class ComicCompQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=160, description="Natural language comic search query.")
    cert_type: CertType = Field(..., description="Certification mode selected by the user.")
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of comparable sales to return.",
    )

    @field_validator("query")
    @classmethod
    def strip_text(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("Field cannot be blank.")
        return stripped_value


class ComicCompList(BaseModel):
    comps: list[ComicComp]


class CompSale(BaseModel):
    title: str
    price: float = Field(..., ge=0)
    date: date
    source: str
    url: str | None = None


class ComicCompSearchResponse(BaseModel):
    query: str
    cert_type: CertType
    median: float | None
    low: float | None
    high: float | None
    usable_count: int
    sales: list[CompSale]


class CompDebugDecision(BaseModel):
    title: str | None
    url: str | None = None
    included: bool
    reasons: list[str]


class ComicCompSearchDebugResponse(BaseModel):
    query: str
    cert_type: CertType
    provider: str
    attempted_queries: list[str]
    fetch_limit: int
    raw_item_count: int
    accepted_count: int
    decisions: list[CompDebugDecision]
