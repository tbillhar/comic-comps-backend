import pytest
from fastapi.testclient import TestClient

from app.config import get_comps_provider_name
from app.main import app
from app.providers.factory import get_comps_provider
from app.providers.sample_provider import SampleCompsProvider


client = TestClient(app)


@pytest.fixture(autouse=True)
def use_sample_provider(monkeypatch):
    monkeypatch.setenv("COMPS_PROVIDER", "sample")


def test_health_check() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_comps_returns_sample_data() -> None:
    response = client.get("/comps")

    assert response.status_code == 200
    payload = response.json()
    assert "comps" in payload
    assert len(payload["comps"]) >= 1
    assert {"title", "issue_number", "grade", "sale_price", "sale_date", "source", "url"}.issubset(
        payload["comps"][0].keys()
    )
    assert isinstance(payload["comps"][0]["sale_price"], int | float)


def test_list_comps_filters_by_title_and_issue() -> None:
    response = client.get("/comps", params={"title": "spider-man", "issue_number": "300"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["comps"]) == 1
    assert payload["comps"][0]["id"] == "asm-300-cgc-9-8-2026-01"


def test_search_comps_returns_stable_contract() -> None:
    response = client.post(
        "/comps",
        json={
            "query": "X-Men 1 CGC 4.0",
            "cert_type": "cgc",
            "max_results": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"] == "X-Men 1 CGC 4.0"
    assert payload["cert_type"] == "cgc"
    assert payload["median"] == 6800
    assert payload["low"] == 6500
    assert payload["high"] == 7100
    assert isinstance(payload["median"], int | float)
    assert isinstance(payload["low"], int | float)
    assert isinstance(payload["high"], int | float)
    assert payload["usable_count"] == 3
    assert payload["sales"][0] == {
        "title": "X-Men 1 CGC 4.0",
        "price": 6500,
        "date": "2026-04-01",
        "source": "sample",
        "url": "https://example.com/x-men-1-cgc-4-0-2026-04-01",
    }
    assert isinstance(payload["sales"][0]["price"], int | float)


def test_search_comps_returns_empty_result_set() -> None:
    response = client.post("/comps", json={"query": "No Matching Title", "cert_type": "cgc"})

    assert response.status_code == 200
    assert response.json()["usable_count"] == 0
    assert response.json()["median"] is None
    assert response.json()["low"] is None
    assert response.json()["high"] is None
    assert response.json()["sales"] == []


def test_debug_search_comps_returns_sample_diagnostics() -> None:
    response = client.post("/comps/debug", json={"query": "X-Men 1 CGC 4.0", "cert_type": "cgc"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "sample"
    assert payload["attempted_queries"] == ["X-Men 1 CGC 4.0"]
    assert payload["accepted_count"] == 3
    assert payload["raw_item_count"] >= 3
    assert any(decision["included"] for decision in payload["decisions"])


def test_search_comps_filters_by_cert_type() -> None:
    response = client.post("/comps", json={"query": "X-Men 1", "cert_type": "raw"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cert_type"] == "raw"
    assert payload["usable_count"] == 1
    assert payload["sales"][0]["title"] == "X-Men 1 Raw"


def test_search_comps_rejects_blank_title() -> None:
    response = client.post("/comps", json={"query": "   ", "cert_type": "cgc"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "query"]


def test_search_comps_rejects_unknown_cert_type() -> None:
    response = client.post("/comps", json={"query": "X-Men 1", "cert_type": "pgx"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "cert_type"]


def test_default_comps_provider_is_apify(monkeypatch) -> None:
    monkeypatch.delenv("COMPS_PROVIDER", raising=False)

    assert get_comps_provider_name() == "apify"


def test_sample_comps_provider_can_be_selected(monkeypatch) -> None:
    monkeypatch.setenv("COMPS_PROVIDER", "sample")

    assert isinstance(get_comps_provider(), SampleCompsProvider)


def test_apify_provider_requires_api_token(monkeypatch) -> None:
    monkeypatch.setenv("COMPS_PROVIDER", "apify")
    monkeypatch.delenv("APIFY_API_TOKEN", raising=False)

    response = client.post("/comps", json={"query": "X-Men 1", "cert_type": "cgc"})

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "sold_comps_provider_not_configured"


def test_apify_provider_normalizes_sold_sales(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, str]]:
            return [
                {
                    "itemId": "123",
                    "url": "https://www.ebay.com/itm/123",
                    "title": "X-Men 1 CGC 4.0",
                    "endedAt": "2026-04-01T12:00:00.000Z",
                    "soldPrice": "6500",
                },
                {
                    "itemId": "124",
                    "url": "https://www.ebay.com/itm/124",
                    "title": "X-Men 1 CGC 4.0",
                    "endedAt": "2026-03-28T12:00:00.000Z",
                    "soldPrice": "6800",
                },
            ]

    def fake_post(*args, **kwargs) -> FakeResponse:
        return FakeResponse()

    monkeypatch.setenv("COMPS_PROVIDER", "apify")
    monkeypatch.setenv("APIFY_API_TOKEN", "test-token")
    monkeypatch.setattr("app.providers.apify_provider.httpx.post", fake_post)

    response = client.post("/comps", json={"query": "X-Men 1 CGC 4.0", "cert_type": "cgc"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["cert_type"] == "cgc"
    assert payload["median"] == 6650
    assert payload["low"] == 6500
    assert payload["high"] == 6800
    assert payload["usable_count"] == 2
    assert payload["sales"][0] == {
        "title": "X-Men 1 CGC 4.0",
        "price": 6500,
        "date": "2026-04-01",
        "source": "ebay",
        "url": "https://www.ebay.com/itm/123",
    }


def test_apify_provider_filters_unrelated_search_results(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, str]]:
            return [
                {
                    "itemId": "hulk-4",
                    "url": "https://www.ebay.com/itm/hulk-4",
                    "title": "Marvel Incredible Hulk #4 1962 CGC 3.0 Intro of Mongu",
                    "endedAt": "2026-04-19T12:00:00.000Z",
                    "soldPrice": "433",
                },
                {
                    "itemId": "jim-98",
                    "url": "https://www.ebay.com/itm/jim-98",
                    "title": "Journey Into Mystery 98 - CGC 3.0 - DOUBLE COVER",
                    "endedAt": "2026-04-19T12:00:00.000Z",
                    "soldPrice": "111",
                },
                {
                    "itemId": "asm-72",
                    "url": "https://www.ebay.com/itm/asm-72",
                    "title": "Amazing Spider-Man 72 CGC 3.0 OW/White Pages",
                    "endedAt": "2026-04-18T12:00:00.000Z",
                    "soldPrice": "24",
                },
                {
                    "itemId": "avengers-1",
                    "url": "https://www.ebay.com/itm/avengers-1",
                    "title": "Avengers #1 CGC 3.0 Mega Key",
                    "endedAt": "2026-04-15T12:00:00.000Z",
                    "soldPrice": "2800",
                },
                {
                    "itemId": "spotlight-28",
                    "url": "https://www.ebay.com/itm/spotlight-28",
                    "title": "Marvel Spotlight #28 - 1976 - CGC Graded 3.0",
                    "endedAt": "2026-04-16T12:00:00.000Z",
                    "soldPrice": "50",
                },
            ]

    def fake_post(*args, **kwargs) -> FakeResponse:
        return FakeResponse()

    monkeypatch.setenv("COMPS_PROVIDER", "apify")
    monkeypatch.setenv("APIFY_API_TOKEN", "test-token")
    monkeypatch.setattr("app.providers.apify_provider.httpx.post", fake_post)

    response = client.post("/comps", json={"query": "Avengers 1 CGC 3.0", "cert_type": "cgc"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["usable_count"] == 1
    assert payload["median"] == 2800
    assert payload["sales"][0]["title"] == "Avengers #1 CGC 3.0 Mega Key"


def test_apify_provider_overfetches_before_local_filtering(monkeypatch) -> None:
    captured_request: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, str]]:
            return []

    def fake_post(*args, **kwargs) -> FakeResponse:
        captured_request["params"] = kwargs["params"]
        captured_request["json"] = kwargs["json"]
        return FakeResponse()

    monkeypatch.setenv("COMPS_PROVIDER", "apify")
    monkeypatch.setenv("APIFY_API_TOKEN", "test-token")
    monkeypatch.setattr("app.providers.apify_provider.httpx.post", fake_post)

    response = client.post("/comps", json={"query": "Avengers 1 CGC 3.0", "cert_type": "cgc", "max_results": 10})

    assert response.status_code == 200
    assert captured_request["params"]["maxItems"] == "50"
    assert captured_request["json"]["count"] == 50


def test_apify_provider_retries_with_normalized_query_when_no_matches(monkeypatch) -> None:
    request_keywords: list[str] = []

    class FakeResponse:
        def __init__(self, payload: list[dict[str, str]]) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, str]]:
            return self.payload

    def fake_post(*args, **kwargs):
        keyword = kwargs["json"]["keywords"][0]
        request_keywords.append(keyword)

        if keyword == "X-Men #1 CGC 4.0":
            return FakeResponse([])

        if keyword == "X Men 1 CGC 4.0":
            return FakeResponse(
                [
                    {
                        "itemId": "xmen-1",
                        "url": "https://www.ebay.com/itm/xmen-1",
                        "title": "X-Men #1 (Marvel, 1963) CGC 4.0",
                        "endedAt": "2026-04-20T12:00:00.000Z",
                        "soldPrice": "6900",
                    }
                ]
            )

        raise AssertionError(f"Unexpected keyword: {keyword}")

    monkeypatch.setenv("COMPS_PROVIDER", "apify")
    monkeypatch.setenv("APIFY_API_TOKEN", "test-token")
    monkeypatch.setattr("app.providers.apify_provider.httpx.post", fake_post)

    response = client.post("/comps", json={"query": "X-Men #1 CGC 4.0", "cert_type": "cgc"})

    assert response.status_code == 200
    payload = response.json()
    assert request_keywords == ["X-Men #1 CGC 4.0", "X Men 1 CGC 4.0"]
    assert payload["usable_count"] == 1
    assert payload["median"] == 6900
    assert payload["sales"][0]["title"] == "X-Men #1 (Marvel, 1963) CGC 4.0"


def test_apify_debug_search_returns_rejection_reasons(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, str]]:
            return [
                {
                    "itemId": "hulk-4",
                    "url": "https://www.ebay.com/itm/hulk-4",
                    "title": "Marvel Incredible Hulk #4 1962 CGC 3.0 Intro of Mongu",
                    "endedAt": "2026-04-19T12:00:00.000Z",
                    "soldPrice": "433",
                },
                {
                    "itemId": "avengers-1",
                    "url": "https://www.ebay.com/itm/avengers-1",
                    "title": "Avengers #1 CGC 3.0 Mega Key",
                    "endedAt": "2026-04-15T12:00:00.000Z",
                    "soldPrice": "2800",
                },
            ]

    def fake_post(*args, **kwargs) -> FakeResponse:
        return FakeResponse()

    monkeypatch.setenv("COMPS_PROVIDER", "apify")
    monkeypatch.setenv("APIFY_API_TOKEN", "test-token")
    monkeypatch.setattr("app.providers.apify_provider.httpx.post", fake_post)

    response = client.post("/comps/debug", json={"query": "Avengers 1 CGC 3.0", "cert_type": "cgc"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "apify"
    assert payload["accepted_count"] == 1
    rejected = next(decision for decision in payload["decisions"] if not decision["included"])
    accepted = next(decision for decision in payload["decisions"] if decision["included"])
    assert rejected["title"] == "Marvel Incredible Hulk #4 1962 CGC 3.0 Intro of Mongu"
    assert "missing_title_term:avengers" in rejected["reasons"]
    assert "issue_number_mismatch:1" in rejected["reasons"]
    assert accepted["title"] == "Avengers #1 CGC 3.0 Mega Key"
    assert accepted["reasons"] == ["matched"]


def test_unsupported_comps_provider_returns_500(monkeypatch) -> None:
    monkeypatch.setenv("COMPS_PROVIDER", "unknown")

    response = client.post("/comps", json={"query": "X-Men 1", "cert_type": "cgc"})

    assert response.status_code == 500
    assert response.json()["detail"]["code"] == "unsupported_comps_provider"


def test_cors_allows_local_frontend_origin() -> None:
    response = client.options(
        "/comps",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def test_cors_allows_deployed_netlify_frontend_origin() -> None:
    response = client.options(
        "/comps",
        headers={
            "Origin": "https://jolly-longma-5797b4.netlify.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://jolly-longma-5797b4.netlify.app"
    assert "content-type" in response.headers["access-control-allow-headers"].lower()
