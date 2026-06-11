def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_missing_api_key_rejected(client):
    r = client.get("/v1/query/overview", headers={"X-GamePulse-Key": ""})
    assert r.status_code == 401


def test_invalid_api_key_rejected(client):
    r = client.get("/v1/query/overview", headers={"X-GamePulse-Key": "nope"})
    assert r.status_code == 401
