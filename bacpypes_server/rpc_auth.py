"""Optional Bearer auth for JSON-RPC HTTP (set BACNET_RPC_API_KEY).

Exempt paths: /server_hello (health / bootstrap verify), /docs*, /redoc, /openapi.json, /
so Swagger UI can load; use Authorize with the same key for Try it out on RPC routes.
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


def install_rpc_auth_if_configured(app) -> None:
    """If BACNET_RPC_API_KEY is set, add Bearer middleware to the FastAPI app."""
    key = (os.environ.get("BACNET_RPC_API_KEY") or "").strip()
    if not key:
        return
    app.add_middleware(BacnetRpcAuthMiddleware, api_key=key)
