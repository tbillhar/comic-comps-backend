from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


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
    assert {"title", "issue_number", "grade", "sale_price", "sale_date", "source"}.issubset(
        payload["comps"][0].keys()
    )


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
    assert payload["median"] == "6800.00"
    assert payload["low"] == "6500.00"
    assert payload["high"] == "7100.00"
    assert payload["usable_count"] == 3
    assert payload["sales"][0] == {
        "title": "X-Men 1 CGC 4.0",
        "price": "6500.00",
        "date": "2026-04-01",
        "source": "sample",
    }


def test_search_comps_returns_empty_result_set() -> None:
    response = client.post("/comps", json={"query": "No Matching Title", "cert_type": "cgc"})

    assert response.status_code == 200
    assert response.json()["usable_count"] == 0
    assert response.json()["median"] is None
    assert response.json()["low"] is None
    assert response.json()["high"] is None
    assert response.json()["sales"] == []


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


def test_cors_allows_local_frontend_origin() -> None:
    response = client.options(
        "/comps",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
