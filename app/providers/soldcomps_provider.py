from datetime import datetime
from decimal import Decimal, InvalidOperation
import logging
import re
from statistics import median
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import DEFAULT_SOLDCOMPS_BASE_URL, get_env, get_int_env, get_required_env
from app.models import (
    CertType,
    ComicComp,
    ComicCompSearchDebugResponse,
    ComicSeriesRangeDebugResponse,
    ComicSeriesRangeResponse,
    CompDebugDecision,
    CompSale,
    IssueConditionCompGroup,
    RangeDebugDecision,
)
from app.providers.base import CompsProvider


logger = logging.getLogger(__name__)


class SoldCompsProvider(CompsProvider):
    def __init__(self) -> None:
        self.api_key = get_required_env("SOLDCOMPS_API_KEY")
        self.base_url = get_env("SOLDCOMPS_BASE_URL", DEFAULT_SOLDCOMPS_BASE_URL)
        self.timeout_seconds = get_int_env("SOLDCOMPS_TIMEOUT_SECONDS", 60)

    def list_comps(self, title: str | None = None, issue_number: str | None = None) -> list[ComicComp]:
        query = " ".join(part for part in [title, issue_number] if part) or "comics"
        return self.search_comps(query=query, cert_type=CertType.CGC, max_results=10)

    def search_comps(self, query: str, cert_type: CertType, max_results: int) -> list[ComicComp]:
        items = self._fetch_items(keyword=query)
        comps = [
            comp
            for item in items
            if (comp := _item_to_comp(item)) is not None
            and _cert_type_matches(comp.title, cert_type)
            and _matches_query(comp.title, query, cert_type)
        ]
        return sorted(comps, key=lambda comp: comp.sale_date, reverse=True)[:max_results]

    def search_series_range(
        self,
        series: str,
        series_start_year: int | None,
        issue_start: int,
        issue_end: int,
        cert_type: CertType,
        max_results_per_group: int,
    ) -> ComicSeriesRangeResponse:
        broad_query = _range_query(series=series, series_start_year=series_start_year, cert_type=cert_type)
        items = self._fetch_items(keyword=broad_query)
        raw_item_count = len(items)
        series_terms = _series_terms(series)

        grouped: dict[tuple[str, str], list[ComicComp]] = {}
        for item in items:
            comp = _item_to_comp(item)
            if comp is None or not _cert_type_matches(comp.title, cert_type):
                continue

            parsed_issue = _extract_issue_number(comp.title, series_terms)
            parsed_condition = _extract_cgc_grade(comp.title) if cert_type == CertType.CGC else "Raw"
            if parsed_issue is None or parsed_condition is None:
                continue
            if not _has_matching_series_phrase(comp.title, series_terms):
                continue
            if _has_variant_or_relaunch_markers(comp.title):
                continue
            if series_start_year is not None and not _matches_series_start_year(comp.title, series_start_year):
                continue
            if not issue_start <= int(parsed_issue) <= issue_end:
                continue

            condition_label = f"CGC {parsed_condition}" if cert_type == CertType.CGC else parsed_condition
            grouped.setdefault((parsed_issue, condition_label), []).append(comp)

        groups: list[IssueConditionCompGroup] = []
        for issue_number, condition in sorted(grouped.keys(), key=lambda key: (int(key[0]), key[1])):
            comps = sorted(grouped[(issue_number, condition)], key=lambda comp: comp.sale_date, reverse=True)[
                :max_results_per_group
            ]
            sales = [
                CompSale(
                    title=comp.title,
                    price=float(comp.sale_price),
                    date=comp.sale_date,
                    source=comp.source,
                    url=comp.url,
                )
                for comp in comps
            ]
            prices = [sale.price for sale in sales]
            groups.append(
                IssueConditionCompGroup(
                    issue_number=issue_number,
                    condition=condition,
                    median=median(prices) if prices else None,
                    low=min(prices) if prices else None,
                    high=max(prices) if prices else None,
                    usable_count=len(sales),
                    sales=sales,
                )
            )

        return ComicSeriesRangeResponse(
            series=series,
            series_start_year=series_start_year,
            issue_start=issue_start,
            issue_end=issue_end,
            cert_type=cert_type,
            broad_query=broad_query,
            raw_item_count=raw_item_count,
            group_count=len(groups),
            groups=groups,
        )

    def debug_search(self, query: str, cert_type: CertType, max_results: int) -> ComicCompSearchDebugResponse:
        items = self._fetch_items(keyword=query)
        decisions: list[CompDebugDecision] = []
        accepted_items: list[ComicComp] = []

        for item in items:
            comp = _item_to_comp(item)
            reasons: list[str] = []
            title = _string_value(item, "title")
            url = _string_value(item, "url")

            if comp is None:
                reasons.append("invalid_item_shape")
            else:
                if not _cert_type_matches(comp.title, cert_type):
                    reasons.append("cert_type_mismatch")
                if not _matches_query(comp.title, query, cert_type):
                    reasons.append("query_terms_missing")

            if comp is not None and not reasons:
                accepted_items.append(comp)

            decisions.append(
                CompDebugDecision(
                    title=title,
                    url=url,
                    included=comp is not None and not reasons,
                    reasons=reasons or ["matched"],
                    parsed_price=float(comp.sale_price) if comp is not None else None,
                    raw_sold_price=_string_value(item, "soldPrice"),
                    raw_total_price=_string_value(item, "totalPrice"),
                    raw_price_fields={key: None if value is None else str(value) for key, value in item.items()},
                )
            )

        return ComicCompSearchDebugResponse(
            query=query,
            cert_type=cert_type,
            provider="soldcomps",
            attempted_queries=[query],
            fetch_limit=max_results,
            raw_item_count=len(items),
            accepted_count=len(accepted_items[:max_results]),
            decisions=decisions,
        )

    def debug_series_range(
        self,
        series: str,
        series_start_year: int | None,
        issue_start: int,
        issue_end: int,
        cert_type: CertType,
        max_results_per_group: int,
    ) -> ComicSeriesRangeDebugResponse:
        broad_query = _range_query(series=series, series_start_year=series_start_year, cert_type=cert_type)
        items = self._fetch_items(keyword=broad_query)
        series_terms = _series_terms(series)
        decisions: list[RangeDebugDecision] = []
        accepted_count = 0

        for item in items:
            comp = _item_to_comp(item)
            title = _string_value(item, "title")
            url = _string_value(item, "url")
            reasons: list[str] = []
            parsed_issue = _extract_issue_number(title or "", series_terms) if title else None
            parsed_condition = _extract_cgc_grade(title or "") if title else None

            if comp is None:
                reasons.append("invalid_item_shape")
            else:
                if not _cert_type_matches(comp.title, cert_type):
                    reasons.append("cert_type_mismatch")
                if parsed_issue is None:
                    reasons.append("issue_not_parsed")
                if parsed_condition is None and cert_type == CertType.CGC:
                    reasons.append("condition_not_parsed")
                if not _has_matching_series_phrase(comp.title, series_terms):
                    reasons.append("series_phrase_mismatch")
                if _has_variant_or_relaunch_markers(comp.title):
                    reasons.append("variant_or_relaunch_marker")
                if series_start_year is not None and not _matches_series_start_year(comp.title, series_start_year):
                    reasons.append(f"series_start_year_mismatch:{series_start_year}")
                if parsed_issue is not None and not issue_start <= int(parsed_issue) <= issue_end:
                    reasons.append(f"issue_out_of_range:{issue_start}-{issue_end}")

            included = comp is not None and not reasons
            if included:
                accepted_count += 1

            decisions.append(
                RangeDebugDecision(
                    title=title,
                    url=url,
                    included=included,
                    reasons=reasons or ["matched"],
                    parsed_issue_number=parsed_issue,
                    parsed_condition=f"CGC {parsed_condition}" if parsed_condition and cert_type == CertType.CGC else parsed_condition,
                    parsed_price=float(comp.sale_price) if comp is not None else None,
                )
            )

        return ComicSeriesRangeDebugResponse(
            series=series,
            series_start_year=series_start_year,
            issue_start=issue_start,
            issue_end=issue_end,
            cert_type=cert_type,
            provider="soldcomps",
            broad_query=broad_query,
            raw_item_count=len(items),
            accepted_count=accepted_count,
            decisions=decisions,
        )

    def _fetch_items(self, keyword: str) -> list[dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }
        params = {"keyword": keyword}

        try:
            response = httpx.get(self.base_url, params=params, headers=headers, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPStatusError as exc:
            logger.exception(
                "SoldComps HTTP error",
                extra={
                    "url": str(exc.request.url) if exc.request else self.base_url,
                    "status_code": exc.response.status_code if exc.response else None,
                    "response_text": exc.response.text[:500] if exc.response and exc.response.text else None,
                },
            )
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "sold_comps_provider_error",
                    "message": "Failed to retrieve sold comps from the configured provider.",
                },
            ) from exc
        except ValueError as exc:
            logger.exception("SoldComps returned invalid JSON")
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "sold_comps_provider_error",
                    "message": "Failed to retrieve sold comps from the configured provider.",
                },
            ) from exc
        except Exception as exc:
            logger.exception("SoldComps request failed")
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "sold_comps_provider_error",
                    "message": "Failed to retrieve sold comps from the configured provider.",
                },
            ) from exc

        items = data.get("items") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "sold_comps_provider_invalid_response",
                    "message": "Sold comps provider returned an unexpected response shape.",
                },
            )

        return [item for item in items if isinstance(item, dict)]


def _item_to_comp(item: dict[str, Any]) -> ComicComp | None:
    title = _string_value(item, "title")
    url = _string_value(item, "url")
    item_id = _string_value(item, "itemId") or url or title
    ended_at = _string_value(item, "endedAt")
    sold_price = _decimal_value(item, "soldPrice")

    if not title or not ended_at or sold_price is None:
        return None

    try:
        sale_date = datetime.fromisoformat(ended_at.replace("Z", "+00:00")).date()
    except ValueError:
        return None

    issue_number = _extract_issue_number(title) or ""
    grade = _extract_cgc_grade(title)
    grade_label = f"CGC {grade}" if grade else ""

    return ComicComp(
        id=f"soldcomps-{item_id}",
        title=title,
        issue_number=issue_number,
        grade=grade_label,
        sale_price=sold_price,
        sale_date=sale_date,
        source="ebay",
        url=url,
    )


def _matches_query(title: str, query: str, cert_type: CertType) -> bool:
    normalized_title = _normalize_text(title)
    normalized_query = _normalize_text(query)
    ignored_terms = {"cgc", "raw"}
    query_terms = [term for term in normalized_query.split() if term not in ignored_terms]
    if cert_type == CertType.CGC and "cgc" not in normalized_title.split():
        return False
    return all(term in normalized_title.split() for term in query_terms)


def _normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", value.casefold()))


def _string_value(item: dict[str, Any], key: str) -> str | None:
    value = item.get(key)
    if value is None:
        return None
    string_value = str(value).strip()
    return string_value or None


def _decimal_value(item: dict[str, Any], key: str) -> Decimal | None:
    value = item.get(key)
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _extract_issue_number(title: str, series_terms: list[str] | None = None) -> str | None:
    direct_match = re.search(r"#\s*(\d{1,5})\b", title)
    if direct_match:
        return direct_match.group(1)

    normalized = _normalize_text(title)
    tokens = normalized.split()

    if series_terms:
        for start_index in range(len(tokens)):
            token_slice = tokens[start_index : start_index + len(series_terms)]
            if token_slice == series_terms:
                search_tokens = tokens[start_index + len(series_terms) :]
                for token in search_tokens:
                    if token.isdigit() and 1 <= int(token) <= 99999:
                        return token
                break

    for token in tokens:
        if token.isdigit() and 1 <= int(token) <= 99999:
            return token

    return None


def _extract_cgc_grade(title: str) -> str | None:
    normalized = _normalize_text(title)
    match = re.search(r"\bcgc\s+([0-9](?:\.[0-9])?|10(?:\.0)?)\b", normalized)
    return match.group(1) if match else None


def _cert_type_matches(title: str, cert_type: CertType) -> bool:
    normalized_title = title.casefold()
    if cert_type == CertType.CGC:
        return "cgc" in normalized_title
    return "cgc" not in normalized_title


def _range_query(series: str, series_start_year: int | None, cert_type: CertType) -> str:
    suffix = "CGC" if cert_type == CertType.CGC else "raw"
    if series_start_year is not None:
        return f"{series} {series_start_year} {suffix}"
    return f"{series} {suffix}"


def _series_terms(series: str) -> list[str]:
    return _normalize_text(series).split()


def _has_matching_series_phrase(title: str, series_terms: list[str]) -> bool:
    normalized_title = _normalize_text(title)
    tokens = normalized_title.split()
    start_index = 0
    while start_index < len(tokens) and tokens[start_index] in {"the"}:
        start_index += 1
    return tokens[start_index : start_index + len(series_terms)] == series_terms


def _matches_series_start_year(title: str, series_start_year: int) -> bool:
    years = {int(match) for match in re.findall(r"\b(19\d{2}|20\d{2})\b", title)}
    if not years:
        return False
    return series_start_year in years


def _has_variant_or_relaunch_markers(title: str) -> bool:
    normalized_title = _normalize_text(title)
    markers = {
        "special edition",
        "variant",
        "facsimile",
        "reprint",
        "annual",
        "one shot",
        "limited series",
        "mini series",
        "mini-series",
    }
    return any(marker in normalized_title for marker in markers)
