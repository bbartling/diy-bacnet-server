"""REST ``POST /bacnet/whois_range`` nested ``{url, request}`` body."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def no_rpc_key(monkeypatch):
    monkeypatch.delenv("BACNET_RPC_API_KEY", raising=False)


def test_openapi_bacnet_whois_rest_example_nested(no_rpc_key):
    from bacpypes_server.rpc_app import rpc_api

    schema = rpc_api.openapi()
    assert "/bacnet/whois_range" in (schema.get("paths") or {})
    post = schema["paths"]["/bacnet/whois_range"]["post"]
    content = (post.get("requestBody") or {}).get("content", {}).get("application/json") or {}
    want = {
        "url": None,
        "request": {"start_instance": 1, "end_instance": 3456799},
    }
    assert content.get("example") == want, content


def test_post_bacnet_whois_nested_body(monkeypatch):
    monkeypatch.delenv("BACNET_RPC_API_KEY", raising=False)

    async def fake_who_is(*args, **kwargs):
        return [{"address": "10.0.0.1", "instance": 2222}]

    import bacpypes_server.rpc_methods as rpc_methods

    monkeypatch.setattr(rpc_methods, "perform_who_is", fake_who_is)

    from bacpypes_server.rpc_app import rpc_api

    c = TestClient(rpc_api)
    r = c.post(
        "/bacnet/whois_range",
        json={
            "url": None,
            "request": {"start_instance": 1, "end_instance": 3456799},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("success") is True
    assert data.get("data", {}).get("devices")
