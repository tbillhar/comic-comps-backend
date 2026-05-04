from statistics import median

from fastapi import HTTPException

from app.models import (
    ComicComp,
    ComicCompQuery,
    ComicCompSearchDebugResponse,
    ComicCompSearchResponse,
    ComicSeriesRangeDebugResponse,
    ComicSeriesRangeQuery,
    ComicSeriesRangeResponse,
    CompSale,
)
from app.providers.base import CompsProvider
from app.providers.factory import get_comps_provider
from app.series_authority import resolve_original_series


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
            url=comp.url,
        )
        for comp in comps
    ]

    prices = [sale.price for sale in sales]
    return ComicCompSearchResponse(
        query=query.query,
        cert_type=query.cert_type,
        median=median(prices) if prices else None,
        low=min(prices) if prices else None,
        high=max(prices) if prices else None,
        usable_count=len(sales),
        sales=sales,
    )


def debug_search_comps(
    query: ComicCompQuery,
    provider: CompsProvider | None = None,
) -> ComicCompSearchDebugResponse:
    selected_provider = provider or get_comps_provider()
    try:
        return selected_provider.debug_search(
            query=query.query,
            cert_type=query.cert_type,
            max_results=query.max_results,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={
                "code": "debug_not_supported",
                "message": "Debug search is not implemented for the configured provider.",
            },
        ) from exc


def search_series_range(
    query: ComicSeriesRangeQuery,
    provider: CompsProvider | None = None,
) -> ComicSeriesRangeResponse:
    selected_provider = provider or get_comps_provider()
    original_series = resolve_original_series(query.series)
    resolved_series = original_series.canonical_name if original_series is not None else query.series
    resolved_series_start_year = (
        query.series_start_year
        if query.series_start_year is not None
        else (original_series.start_year if original_series is not None else None)
    )
    try:
        return selected_provider.search_series_range(
            series=resolved_series,
            series_start_year=resolved_series_start_year,
            issue_start=query.issue_start,
            issue_end=query.issue_end,
            cert_type=query.cert_type,
            max_results_per_group=query.max_results_per_group,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={
                "code": "range_search_not_supported",
                "message": "Range search is not implemented for the configured provider.",
            },
        ) from exc


def debug_series_range(
    query: ComicSeriesRangeQuery,
    provider: CompsProvider | None = None,
) -> ComicSeriesRangeDebugResponse:
    selected_provider = provider or get_comps_provider()
    original_series = resolve_original_series(query.series)
    resolved_series = original_series.canonical_name if original_series is not None else query.series
    resolved_series_start_year = (
        query.series_start_year
        if query.series_start_year is not None
        else (original_series.start_year if original_series is not None else None)
    )
    try:
        return selected_provider.debug_series_range(
            series=resolved_series,
            series_start_year=resolved_series_start_year,
            issue_start=query.issue_start,
            issue_end=query.issue_end,
            cert_type=query.cert_type,
            max_results_per_group=query.max_results_per_group,
        )
    except NotImplementedError as exc:
        raise HTTPException(
            status_code=501,
            detail={
                "code": "range_debug_not_supported",
                "message": "Range debug search is not implemented for the configured provider.",
            },
        ) from exc
