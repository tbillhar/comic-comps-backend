from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class ComicComp(BaseModel):
    id: str = Field(..., description="Stable comparable sale identifier.")
    title: str
    issue_number: str
    grade: str
    sale_price: Decimal = Field(..., ge=0)
    sale_date: date
    source: str


class ComicCompQuery(BaseModel):
    title: str = Field(..., min_length=1, max_length=120, description="Comic title to search.")
    issue_number: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        description="Optional issue number to narrow the search.",
    )
    grade: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        description="Optional grading label such as CGC 9.8.",
    )
    max_results: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of comparable sales to return.",
    )

    @field_validator("title", "issue_number", "grade")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError("Field cannot be blank.")
        return stripped_value


class ComicCompList(BaseModel):
    comps: list[ComicComp]


class ComicCompSearchResponse(BaseModel):
    query: ComicCompQuery
    count: int
    comps: list[ComicComp]
