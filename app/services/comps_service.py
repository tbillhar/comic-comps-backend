from decimal import Decimal
from statistics import median

from app.models import ComicComp, ComicCompQuery, ComicCompSearchResponse, CompSale
from app.providers.base import CompsProvider
from app.providers.factory import get_comps_provider


def list_sample_comps(title: str | None = None, issue_number: str | None = None) -> list[ComicComp]:
    return get_comps_provider().list_comps(title=title, issue_number=issue_number)


def search_comps(query: ComicCompQuery, provider: CompsProvider | None = None) -> ComicCompSearchResponse:
    selected_provider = provider or get_comps_provider()
    comps = selected_provider.search_comps(
        query=query.query,
        cert_type=query.cert_type,
        max_results=query.max_results,
    )
    sales = [
        CompSale(
            title=comp.title,
            price=comp.sale_price,
            date=comp.sale_date,
            source=comp.source,
        )
        for comp in comps
    ]

    prices = [sale.price for sale in sales]
    return ComicCompSearchResponse(
        query=query.query,
        cert_type=query.cert_type,
        median=Decimal(str(median(prices))) if prices else None,
        low=min(prices) if prices else None,
        high=max(prices) if prices else None,
        usable_count=len(sales),
        sales=sales,
    )
