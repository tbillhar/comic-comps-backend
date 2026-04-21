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
