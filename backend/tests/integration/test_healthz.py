def test_healthz_returns_200_when_database_is_reachable(client):
    assert client.get("/healthz").status_code == 200


def test_healthz_returns_503_when_database_is_unreachable(unreachable_client):
    assert unreachable_client.get("/healthz").status_code == 503
