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
    assert payload["comps"][0]["title"] == "Amazing Spider-Man"


def test_list_comps_filters_by_title_and_issue() -> None:
    response = client.get("/comps", params={"title": "spider", "issue_number": "300"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["comps"]) == 1
    assert payload["comps"][0]["id"] == "asm-300-cgc-9-8-2026-01"


def test_search_comps_returns_stable_contract() -> None:
    response = client.post(
        "/comps",
        json={
            "title": "Amazing Spider-Man",
            "issue_number": "300",
            "grade": "CGC 9.8",
            "max_results": 5,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query"]["title"] == "Amazing Spider-Man"
    assert payload["query"]["issue_number"] == "300"
    assert payload["query"]["grade"] == "CGC 9.8"
    assert payload["count"] == 1
    assert payload["comps"][0] == {
        "id": "asm-300-cgc-9-8-2026-01",
        "title": "Amazing Spider-Man",
        "issue_number": "300",
        "grade": "CGC 9.8",
        "sale_price": "7200.00",
        "sale_date": "2026-01-15",
        "source": "sample",
    }


def test_search_comps_returns_empty_result_set() -> None:
    response = client.post("/comps", json={"title": "No Matching Title"})

    assert response.status_code == 200
    assert response.json()["count"] == 0
    assert response.json()["comps"] == []


def test_search_comps_rejects_blank_title() -> None:
    response = client.post("/comps", json={"title": "   "})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "title"]


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
