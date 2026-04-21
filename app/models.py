from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class ComicComp(BaseModel):
    id: str = Field(..., description="Stable comparable sale identifier.")
    title: str
    issue_number: str
    grade: str
    sale_price: Decimal = Field(..., ge=0)
    sale_date: date
    source: str


class ComicCompList(BaseModel):
    comps: list[ComicComp]
