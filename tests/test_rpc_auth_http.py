"""HTTP Bearer auth for BACnet RPC (BACNET_RPC_API_KEY)."""

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from bacpypes_server.rpc_auth import (
    BacnetRpcAuthMiddleware,
    rpc_auth_path_exempt,
)


async def _hello(_: Request):
    return JSONResponse({"ok": True})


_TEST_KEY = "a" * 32  # compare_digest-safe length vs wrong token


def _make_app_with_auth():
    app = Starlette(
        routes=[
            Route("/server_hello", _hello, methods=["POST"]),
            Route("/client_read_property", _hello, methods=["POST"]),
            Route("/openapi.json", _hello, methods=["GET"]),
        ]
    )
    app.add_middleware(BacnetRpcAuthMiddleware, api_key=_TEST_KEY)
    return app


def test_path_exempt_server_hello():
    assert rpc_auth_path_exempt("/server_hello") is True
    assert rpc_auth_path_exempt("/client_read_property") is False
    assert rpc_auth_path_exempt("/docs") is True
    assert rpc_auth_path_exempt("/docs/oauth2-redirect") is True
    assert rpc_auth_path_exempt("/openapi.json") is True


def test_server_hello_without_bearer_ok():
    client = TestClient(_make_app_with_auth())
    r = client.post("/server_hello")
    assert r.status_code == 200


def test_rpc_without_bearer_401():
    client = TestClient(_make_app_with_auth())
    r = client.post("/client_read_property")
    assert r.status_code == 401


def test_rpc_wrong_bearer_403():
    client = TestClient(_make_app_with_auth())
    r = client.post(
        "/client_read_property",
        headers={"Authorization": "Bearer " + "b" * 32},
    )
    assert r.status_code == 403


def test_rpc_correct_bearer_ok():
    client = TestClient(_make_app_with_auth())
    r = client.post(
        "/client_read_property",
        headers={"Authorization": "Bearer " + _TEST_KEY},
    )
    assert r.status_code == 200


def test_openapi_exempt_without_bearer():
    client = TestClient(_make_app_with_auth())
    r = client.get("/openapi.json")
    assert r.status_code == 200
