from fastapi.testclient import TestClient

from main import app


def test_liveness() -> None:
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_exposes_combined_image_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")
    assert "/api/v1/poetry/match" in response.json()["paths"]
