"""HTTP tests for /modbus/read_registers."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def no_rpc_key(monkeypatch):
    monkeypatch.delenv("BACNET_RPC_API_KEY", raising=False)


def test_modbus_openapi_lists_path(no_rpc_key):
    from bacpypes_server.rpc_app import rpc_api

    schema = rpc_api.openapi()
    assert "/modbus/read_registers" in (schema.get("paths") or {})


def test_modbus_read_registers_http_mocked(no_rpc_key, monkeypatch):
    from bacpypes_server.rpc_app import rpc_api

    async def fake_to_thread(func, *args, **kwargs):
        assert func.__name__ == "execute_modbus_read_request"
        payload = args[0]
        return {
            "ok": True,
            "host": payload["host"],
            "port": payload["port"],
            "unit_id": payload["unit_id"],
            "timeout": payload["timeout"],
            "readings": [
                {
                    "address": 150,
                    "function": "holding",
                    "count": 1,
                    "success": True,
                    "words": [2410],
                    "decoded": 241.0,
                    "label": "grid_l1n_x01V",
                    "error": None,
                }
            ],
        }

    monkeypatch.setattr(
        "bacpypes_server.modbus_routes.asyncio.to_thread",
        fake_to_thread,
    )

    c = TestClient(rpc_api)
    r = c.post(
        "/modbus/read_registers",
        json={
            "host": "10.200.200.170",
            "port": 502,
            "unit_id": 1,
            "timeout": 5.0,
            "registers": [
                {
                    "address": 150,
                    "count": 1,
                    "function": "holding",
                    "decode": "uint16",
                    "scale": 0.1,
                    "label": "grid_l1n_x01V",
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["readings"][0]["address"] == 150
    assert body["readings"][0]["decoded"] == pytest.approx(241.0)


def test_modbus_decode_count_validation(no_rpc_key):
    from bacpypes_server.rpc_app import rpc_api

    c = TestClient(rpc_api)
    r = c.post(
        "/modbus/read_registers",
        json={
            "host": "10.0.0.1",
            "registers": [
                {"address": 500, "count": 1, "function": "input", "decode": "float32"}
            ],
        },
    )
    assert r.status_code == 422


def test_modbus_validation_empty_host(no_rpc_key):
    from bacpypes_server.rpc_app import rpc_api

    c = TestClient(rpc_api)
    r = c.post(
        "/modbus/read_registers",
        json={
            "host": "  ",
            "registers": [{"address": 0, "count": 1, "function": "holding"}],
        },
    )
    assert r.status_code == 422
