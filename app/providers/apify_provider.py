from datetime import datetime
from decimal import Decimal, InvalidOperation
import re
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from app.config import (
    DEFAULT_APIFY_DAYS_TO_SCRAPE,
    DEFAULT_APIFY_EBAY_SITE,
    DEFAULT_APIFY_MAX_TOTAL_CHARGE_USD,
    get_env,
    get_int_env,
    get_required_env,
)
from app.models import CertType, ComicComp
from app.providers.base import CompsProvider

MIN_PROVIDER_FETCH_RESULTS = 50
MAX_PROVIDER_FETCH_RESULTS = 100


class ApifySoldCompsProvider(CompsProvider):
    def __init__(self) -> None:
        self.api_token = get_required_env("APIFY_API_TOKEN")
        self.actor_id = get_env("APIFY_ACTOR_ID", "caffein.dev~ebay-sold-listings")
        self.ebay_site = get_env("APIFY_EBAY_SITE", DEFAULT_APIFY_EBAY_SITE)
        self.days_to_scrape = get_int_env("APIFY_DAYS_TO_SCRAPE", DEFAULT_APIFY_DAYS_TO_SCRAPE)
        self.max_total_charge_usd = get_env("APIFY_MAX_TOTAL_CHARGE_USD", DEFAULT_APIFY_MAX_TOTAL_CHARGE_USD)
        self.timeout_seconds = get_int_env("APIFY_TIMEOUT_SECONDS", 120)

    def list_comps(self, title: str | None = None, issue_number: str | None = None) -> list[ComicComp]:
        query = " ".join(part for part in [title, issue_number] if part) or "comics"
        return self.search_comps(query=query, cert_type=CertType.CGC, max_results=10)

    def search_comps(self, query: str, cert_type: CertType, max_results: int) -> list[ComicComp]:
        parsed_query = _parse_query(query, cert_type)
        fetch_limit = _provider_fetch_limit(max_results)
        items = self._fetch_items(query=query, max_results=fetch_limit)
        comps = [
            comp
            for item in items
            if (comp := _item_to_comp(item)) is not None
            and _cert_type_matches(comp.title, cert_type)
            and _matches_requested_comic(comp.title, parsed_query)
        ]
        return sorted(comps, key=lambda comp: comp.sale_date, reverse=True)[:max_results]

    def _fetch_items(self, query: str, max_results: int) -> list[dict[str, Any]]:
        url = (
            "https://api.apify.com/v2/acts/"
            f"{quote(self.actor_id, safe='~')}/run-sync-get-dataset-items"
        )
        params = {
            "token": self.api_token,
            "format": "json",
            "clean": "true",
            "maxItems": str(max_results),
            "maxTotalChargeUsd": self.max_total_charge_usd,
        }
        payload = {
            "keywords": [query],
            "count": max_results,
            "daysToScrape": self.days_to_scrape,
            "ebaySite": self.ebay_site,
            "sortOrder": "endedRecently",
            "itemCondition": "any",
            "currencyMode": "USD",
            "detailedSearch": False,
        }

        try:
            response = httpx.post(url, params=params, json=payload, timeout=self.timeout_seconds)
            response.raise_for_status()
            data = response.json()
        except RuntimeError as exc:
            raise exc
        except Exception as exc:
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "sold_comps_provider_error",
                    "message": "Failed to retrieve sold comps from the configured provider.",
                },
            ) from exc

        if not isinstance(data, list):
            raise HTTPException(
                status_code=502,
                detail={
                    "code": "sold_comps_provider_invalid_response",
                    "message": "Sold comps provider returned an unexpected response shape.",
                },
            )

        return [item for item in data if isinstance(item, dict)]


def _item_to_comp(item: dict[str, Any]) -> ComicComp | None:
    title = _string_value(item, "title")
    url = _string_value(item, "url")
    item_id = _string_value(item, "itemId") or url or title
    ended_at = _string_value(item, "endedAt")
    price = _decimal_value(item, "soldPrice") or _decimal_value(item, "totalPrice")

    if not title or not ended_at or price is None:
        return None

    try:
        sale_date = datetime.fromisoformat(ended_at.replace("Z", "+00:00")).date()
    except ValueError:
        return None

    return ComicComp(
        id=f"apify-{item_id}",
        title=title,
        issue_number="",
        grade="",
        sale_price=price,
        sale_date=sale_date,
        source="ebay",
        url=url,
    )


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


def _cert_type_matches(title: str, cert_type: CertType) -> bool:
    normalized_title = title.casefold()
    if cert_type == CertType.CGC:
        return "cgc" in normalized_title

    return "cgc" not in normalized_title


def _parse_query(query: str, cert_type: CertType) -> dict[str, object]:
    normalized_query = _normalize_text(query)
    grade = _extract_grade(normalized_query) if cert_type == CertType.CGC else None
    issue_number = _extract_issue_number(normalized_query)

    title_terms = [
        term
        for term in normalized_query.split()
        if term not in {"cgc", "raw"}
        and term != grade
        and term != issue_number
        and not _is_grade_token(term)
    ]

    return {
        "title_terms": title_terms,
        "issue_number": issue_number,
        "grade": grade,
    }


def _matches_requested_comic(title: str, parsed_query: dict[str, object]) -> bool:
    normalized_title = _normalize_text(title)
    title_terms = parsed_query["title_terms"]
    issue_number = parsed_query["issue_number"]
    grade = parsed_query["grade"]

    return (
        isinstance(title_terms, list)
        and all(term in normalized_title.split() for term in title_terms)
        and (not issue_number or _has_issue_number(normalized_title, str(issue_number)))
        and (not grade or _has_grade(normalized_title, str(grade)))
    )


def _normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", value.casefold()))


def _extract_issue_number(normalized_query: str) -> str | None:
    terms = normalized_query.split()
    ignored_next = False
    for index, term in enumerate(terms):
        if ignored_next:
            ignored_next = False
            continue
        if term in {"cgc", "raw"}:
            ignored_next = term == "cgc"
            continue
        if term.isdigit():
            return term

    return None


def _extract_grade(normalized_query: str) -> str | None:
    match = re.search(r"\bcgc\s+([0-9](?:\.[0-9])?|10(?:\.0)?)\b", normalized_query)
    if not match:
        return None
    return match.group(1)


def _is_grade_token(term: str) -> bool:
    return re.fullmatch(r"[0-9](?:\.[0-9])?|10(?:\.0)?", term) is not None


def _has_issue_number(normalized_title: str, issue_number: str) -> bool:
    return issue_number in normalized_title.split()


def _has_grade(normalized_title: str, grade: str) -> bool:
    return re.search(rf"\bcgc\s+{re.escape(grade)}\b", normalized_title) is not None


def _provider_fetch_limit(max_results: int) -> int:
    return min(MAX_PROVIDER_FETCH_RESULTS, max(MIN_PROVIDER_FETCH_RESULTS, max_results * 5))
