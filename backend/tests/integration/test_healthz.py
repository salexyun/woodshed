from fastapi.testclient import TestClient

from woodshed.main import app


def test_healthz_returns_200():
    assert TestClient(app).get("/healthz").status_code == 200
