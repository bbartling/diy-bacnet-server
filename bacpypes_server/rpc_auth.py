"""Optional Bearer auth for JSON-RPC HTTP (set ``BACNET_RPC_API_KEY``).

When the key is set, all JSON-RPC ``POST /<method>`` routes require
``Authorization: Bearer <key>`` except:

- ``GET /`` and ``POST /server_hello`` (minimal reachability checks)

If OpenAPI docs are enabled (see ``bacpypes_server.env_features.openapi_docs_enabled``),
``/docs``, ``/redoc``, and ``/openapi.json`` (and static assets under them) are also
exempt so the browser can load Swagger; use **Authorize** in Swagger for Try-it-out
calls. When docs are off, those routes are not mounted (``GET /docs`` → 404).
"""

from __future__ import annotations

import os
import secrets
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from bacpypes_server.env_features import openapi_docs_enabled


def rpc_auth_path_exempt(path: str) -> bool:
    if path == "/server_hello":
        return True
    if path == "/":
        return True
    if openapi_docs_enabled():
        if path in ("/docs", "/redoc", "/openapi.json"):
            return True
        if path.startswith("/docs/") or path.startswith("/redoc/"):
            return True
    return False


class BacnetRpcAuthMiddleware(BaseHTTPMiddleware):
    """Require Authorization: Bearer <BACNET_RPC_API_KEY> except exempt paths."""

    def __init__(self, app: ASGIApp, api_key: str):
        super().__init__(app)
        self._api_key = api_key.strip()
        if not self._api_key:
            raise ValueError("BacnetRpcAuthMiddleware requires non-empty api_key")

    async def dispatch(self, request: Request, call_next: Callable):
        if rpc_auth_path_exempt(request.url.path):
            return await call_next(request)
        auth = request.headers.get("Authorization") or ""
        if not auth.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Missing or invalid Authorization header"},
                status_code=401,
            )
        token = auth[7:].strip()
        if not secrets.compare_digest(token, self._api_key):
            return JSONResponse({"detail": "Invalid API key"}, status_code=403)
        return await call_next(request)


def install_openapi_bearer_for_swagger(app) -> None:
    """
    Inject BearerAuth into the generated OpenAPI schema (for ``app.openapi()`` / Swagger).
    When ``BACNET_RPC_API_KEY`` is set, middleware enforces Bearer on JSON-RPC routes; OpenAPI
    UI paths are exempt only when docs are enabled (see ``rpc_auth_path_exempt``).
    """

    def _custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        from fastapi.openapi.utils import get_openapi

        schema = get_openapi(
            title=app.title,
            version=app.version,
            openapi_version=app.openapi_version,
            description=app.description,
            routes=app.routes,
            tags=getattr(app, "openapi_tags", None),
            servers=getattr(app, "servers", None),
        )
        schema["components"] = schema.get("components") or {}
        schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "API Key",
                "description": (
                    "When BACNET_RPC_API_KEY is set, use that same value. "
                    "Send `Authorization: Bearer <key>` on JSON-RPC requests."
                ),
            }
        }
        schema["security"] = [{"BearerAuth": []}]
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = _custom_openapi


def install_openapi_servers_url_from_env(app) -> None:
    """If BACNET_SWAGGER_SERVERS_URL is set (e.g. /bacnet behind Caddy), set OpenAPI servers so Swagger Try it out uses HTTPS + prefix."""
    base = (os.environ.get("BACNET_SWAGGER_SERVERS_URL") or "").strip()
    if not base:
        return
    _prev = app.openapi

    def _combined_openapi():
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = _prev()
        schema["servers"] = [{"url": base}]
        return schema

    app.openapi = _combined_openapi


def install_rpc_auth_if_configured(app) -> None:
    """If BACNET_RPC_API_KEY is set, add Bearer middleware to the FastAPI app."""
    key = (os.environ.get("BACNET_RPC_API_KEY") or "").strip()
    if not key:
        return
    app.add_middleware(BacnetRpcAuthMiddleware, api_key=key)
