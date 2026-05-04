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


class ComicSeriesRangeQuery(BaseModel):
    series: str = Field(..., min_length=1, max_length=120, description="Series name, for example X-Men.")
    series_start_year: int | None = Field(
        default=None,
        ge=1900,
        le=2100,
        description="Optional series launch year used to disambiguate relaunches and variants.",
    )
    issue_start: int = Field(..., ge=1, le=99999, description="Starting issue number, inclusive.")
    issue_end: int = Field(..., ge=1, le=99999, description="Ending issue number, inclusive.")
    cert_type: CertType = Field(..., description="Certification mode selected by the user.")
    max_results_per_group: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Maximum number of comparable sales to keep for each issue/condition group.",
    )

    @field_validator("series")
    @classmethod
    def strip_series(cls, value: str) -> str:
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("Field cannot be blank.")
        return stripped_value

    @field_validator("issue_end")
    @classmethod
    def validate_issue_range(cls, value: int, info) -> int:
        issue_start = info.data.get("issue_start")
        if issue_start is not None and value < issue_start:
            raise ValueError("issue_end must be greater than or equal to issue_start.")
        return value


class IssueConditionCompGroup(BaseModel):
    issue_number: str
    condition: str
    median: float | None
    low: float | None
    high: float | None
    usable_count: int
    sales: list[CompSale]


class ComicSeriesRangeResponse(BaseModel):
    series: str
    series_start_year: int | None = None
    issue_start: int
    issue_end: int
    cert_type: CertType
    broad_query: str
    raw_item_count: int
    group_count: int
    groups: list[IssueConditionCompGroup]


class CompDebugDecision(BaseModel):
    title: str | None
    url: str | None = None
    included: bool
    reasons: list[str]
    parsed_price: float | None = None
    raw_sold_price: str | None = None
    raw_total_price: str | None = None
    raw_price_fields: dict[str, str | None] = Field(default_factory=dict)


class ComicCompSearchDebugResponse(BaseModel):
    query: str
    cert_type: CertType
    provider: str
    attempted_queries: list[str]
    fetch_limit: int
    raw_item_count: int
    accepted_count: int
    decisions: list[CompDebugDecision]
