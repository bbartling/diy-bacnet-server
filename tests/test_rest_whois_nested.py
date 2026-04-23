"""Ensure nested REST Who-Is route is not exposed."""

def test_openapi_does_not_expose_nested_bacnet_whois_route(monkeypatch):
    monkeypatch.delenv("BACNET_RPC_API_KEY", raising=False)
    from bacpypes_server.rpc_app import rpc_api

    schema = rpc_api.openapi()
    assert "/bacnet/whois_range" not in (schema.get("paths") or {})
