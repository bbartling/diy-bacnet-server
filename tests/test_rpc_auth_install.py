"""install_rpc_auth_if_configured + env BACNET_RPC_API_KEY (fresh FastAPI, no rpc_app import)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from bacpypes_server.rpc_auth import install_rpc_auth_if_configured


@pytest.fixture
def app_with_rpc_auth(monkeypatch):
    monkeypatch.setenv("BACNET_RPC_API_KEY", "test-secret-key-for-mw")
    app = FastAPI()

    @app.post("/client_read_property")
    async def _rpc():
        return {"ok": True}

    install_rpc_auth_if_configured(app)
    return app


def test_install_skips_middleware_when_key_unset(monkeypatch):
    monkeypatch.delenv("BACNET_RPC_API_KEY", raising=False)
    app = FastAPI()

    @app.post("/x")
    async def _x():
        return {"ok": True}

    install_rpc_auth_if_configured(app)
    c = TestClient(app)
    assert c.post("/x").status_code == 200


def test_install_skips_middleware_when_key_empty(monkeypatch):
    monkeypatch.setenv("BACNET_RPC_API_KEY", "   ")
    app = FastAPI()

    @app.post("/x")
    async def _x():
        return {"ok": True}

    install_rpc_auth_if_configured(app)
    c = TestClient(app)
    assert c.post("/x").status_code == 200


def test_installed_middleware_401_without_bearer(app_with_rpc_auth):
    c = TestClient(app_with_rpc_auth)
    assert c.post("/client_read_property").status_code == 401


def test_installed_middleware_401_malformed_authorization(app_with_rpc_auth):
    c = TestClient(app_with_rpc_auth)
    r = c.post(
        "/client_read_property",
        headers={"Authorization": "Token not-bearer"},
    )
    assert r.status_code == 401


def test_installed_middleware_403_wrong_bearer(app_with_rpc_auth):
    c = TestClient(app_with_rpc_auth)
    r = c.post(
        "/client_read_property",
        headers={"Authorization": "Bearer wrong-key"},
    )
    assert r.status_code == 403


def test_installed_middleware_200_correct_bearer(app_with_rpc_auth):
    c = TestClient(app_with_rpc_auth)
    r = c.post(
        "/client_read_property",
        headers={"Authorization": "Bearer test-secret-key-for-mw"},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_openapi_matches_open_fdd_bearerauth_shape():
    """Same components.securitySchemes + global security as open_fdd/platform/api/main.py."""
    from bacpypes_server.rpc_app import rpc_api

    data = rpc_api.openapi()
    bearer = data["components"]["securitySchemes"]["BearerAuth"]
    assert bearer == {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "API Key",
        "description": (
            "When BACNET_RPC_API_KEY is set, use that value "
            "(Open-FDD: same as `OFDD_BACNET_SERVER_API_KEY` in stack/.env). "
            "Send `Authorization: Bearer <key>` on JSON-RPC requests."
        ),
    }
    assert data.get("security") == [{"BearerAuth": []}]
