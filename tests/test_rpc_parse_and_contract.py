"""Parse helpers and JSON-RPC API contract (TestClient) — no live BACnet."""

import os

import pytest
from bacpypes3.primitivedata import ObjectIdentifier

from bacpypes_server.rpc_methods import parse_object_identifier


def _rpc_auth_headers() -> dict:
    """When BACNET_RPC_API_KEY is set, RPC routes require Bearer."""
    k = (os.environ.get("BACNET_RPC_API_KEY") or "").strip()
    return {"Authorization": f"Bearer {k}"} if k else {}


def test_parse_object_identifier_valid():
    oid = parse_object_identifier("analog-value,1")
    assert isinstance(oid, ObjectIdentifier)
    assert str(oid) == "analogValue,1" or "analog-value,1" in str(oid).lower().replace(" ", "")


def test_parse_object_identifier_with_spaces():
    oid = parse_object_identifier("  analog-input , 2  ")
    assert isinstance(oid, ObjectIdentifier)


def test_parse_object_identifier_invalid_no_comma():
    with pytest.raises(ValueError, match="objectType,instanceNumber"):
        parse_object_identifier("analog-value")


def test_parse_object_identifier_invalid_bad_instance():
    with pytest.raises(ValueError):
        parse_object_identifier("analog-value,notanumber")


# --- JSON-RPC API contract (HTTP layer) ---

@pytest.fixture
def rpc_app():
    """RPC app without BACnet stack (client_utils.app not set). Use for server_hello only."""
    from bacpypes_server.rpc_app import rpc_api
    return rpc_api


def test_server_hello_via_http(rpc_app):
    """POST /server_hello returns 200 and JSON-RPC result with message."""
    from fastapi.testclient import TestClient
    client = TestClient(rpc_app)
    payload = {
        "jsonrpc": "2.0",
        "id": "0",
        "method": "server_hello",
        "params": {},
    }
    resp = client.post("/server_hello", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert "message" in data["result"]
    assert "BACnet RPC API ready" in data["result"]["message"]


def test_client_whois_range_request_shape(rpc_app):
    """POST /client_whois_range with valid params returns (may error if no BACnet app)."""
    from fastapi.testclient import TestClient
    client = TestClient(rpc_app)
    payload = {
        "jsonrpc": "2.0",
        "id": "0",
        "method": "client_whois_range",
        "params": {"request": {"start_instance": 1, "end_instance": 100}},
    }
    resp = client.post("/client_whois_range", json=payload, headers=_rpc_auth_headers())
    # 200 with JSON-RPC response; body may be result or error depending on whether app is set
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data or "error" in data
    if "result" in data:
        assert "data" in data["result"] or "success" in data["result"]
    if "error" in data:
        assert "message" in data["error"] or "data" in data["error"]


def test_server_read_schedule_request_shape(rpc_app):
    """POST /server_read_schedule accepts request wrapper and returns JSON-RPC result."""
    from fastapi.testclient import TestClient

    client = TestClient(rpc_app)
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "server_read_schedule",
        "params": {"request": {"name": "occupancy-schedule"}},
    }
    resp = client.post("/server_read_schedule", json=payload, headers=_rpc_auth_headers())
    assert resp.status_code == 200
    data = resp.json()
    assert "result" in data
    assert "status" in data["result"]
