import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from woodshed.api import router
from woodshed.main import serve_spa

INDEX = "<!doctype html><title>Woodshed</title>"
SECRET = "do not serve"


@pytest.fixture
def client(tmp_path) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text(INDEX)
    (dist / "assets" / "app.js").write_text("console.log('hi')")
    (tmp_path / "secret.txt").write_text(SECRET)
    app = FastAPI()
    app.include_router(router)
    serve_spa(app, dist)
    return TestClient(app)


@pytest.mark.parametrize("path", ["/", "/session/1", "/settings"])
def test_client_routes_return_index_html(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert response.text == INDEX


def test_assets_are_served(client):
    assert client.get("/assets/app.js").text == "console.log('hi')"


def test_missing_asset_is_404(client):
    assert client.get("/assets/gone.js").status_code == 404


def test_unknown_api_path_is_404_json(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_wrong_method_on_api_route_is_405(client):
    assert client.get("/api/onboarding").status_code == 405


def test_non_get_outside_api_is_not_index_html(client):
    assert client.post("/session/1").text != INDEX


@pytest.mark.parametrize(
    "path", ["/assets/..%2F..%2Fsecret.txt", "/assets/../../secret.txt"]
)
def test_traversal_does_not_escape_dist(client, path):
    assert SECRET not in client.get(path).text
