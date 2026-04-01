"""Optional Bearer auth for JSON-RPC HTTP (set BACNET_RPC_API_KEY).

Exempt paths: /server_hello (health / bootstrap verify), /docs*, /redoc, /openapi.json, /
so Swagger UI can load.

OpenAPI uses the same BearerAuth scheme and global security as Open-FDD (HTTP Bearer,
bearerFormat \"API Key\") so **Authorize** in Swagger UI behaves the same; use the same
paste-the-key flow as the platform API docs.
"""

from __future__ import annotations

import os
import secrets
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp


def rpc_auth_path_exempt(path: str) -> bool:
    if path == "/server_hello":
        return True
    if path in ("/", "/redoc", "/openapi.json"):
        return True
    if path.startswith("/docs"):
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
    Inject the same OpenAPI Bearer pattern as Open-FDD (open_fdd/platform/api/main.py):
    components.securitySchemes.BearerAuth (http/bearer, bearerFormat API Key) and
    top-level security so Swagger UI shows Authorize and sends Authorization on Try it out.
    Always applied so the UI matches the platform API; middleware still enforces only when
    BACNET_RPC_API_KEY is set.
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
                    "When BACNET_RPC_API_KEY is set, use that value "
                    "(Open-FDD: same as `OFDD_BACNET_SERVER_API_KEY` in stack/.env). "
                    "In Swagger: click Authorize, paste the key, then Try it out."
                ),
            }
        }
        schema["security"] = [{"BearerAuth": []}]
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = _custom_openapi


def install_rpc_auth_if_configured(app) -> None:
    """If BACNET_RPC_API_KEY is set, add Bearer middleware to the FastAPI app."""
    key = (os.environ.get("BACNET_RPC_API_KEY") or "").strip()
    if not key:
        return
    app.add_middleware(BacnetRpcAuthMiddleware, api_key=key)
