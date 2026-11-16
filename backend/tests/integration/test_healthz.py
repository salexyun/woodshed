def test_healthz_returns_200_when_database_is_reachable(client):
    assert client.get("/healthz").status_code == 200


def test_healthz_returns_503_when_database_is_unreachable(unreachable_client):
    assert unreachable_client.get("/healthz").status_code == 503


def test_healthz_reports_the_deployed_git_sha(client, monkeypatch):
    monkeypatch.setenv("GIT_SHA", "abc123")
    assert client.get("/healthz").json() == {"status": "ok", "version": "abc123"}
