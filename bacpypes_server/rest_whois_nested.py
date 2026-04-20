"""Optional REST ``POST /bacnet/whois_range`` with nested ``{url, request}`` JSON.

Some multi-gateway UIs send a ``url`` field alongside ``request``; on this
single-gateway service ``url`` is ignored. JSON-RPC (``POST /client_whois_range``)
is unchanged.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException
from fastapi_jsonrpc import BaseError as JsonRpcBaseError
from pydantic import BaseModel, ConfigDict, Field

from bacpypes_server.models import BaseResponse, DeviceInstanceRange
from bacpypes_server import rpc_methods

logger = logging.getLogger("rest_whois_nested")


def _whois_nested_body_json_schema_extra(schema: dict) -> None:
    """Order ``url`` before ``request`` in generated schema; stable example."""
    props = schema.get("properties") or {}
    if "url" in props and "request" in props:
        schema["properties"] = {"url": props["url"], "request": props["request"]}
    schema["example"] = {
        "url": None,
        "request": {"start_instance": 1, "end_instance": 3456799},
    }


class WhoIsRangeNestedBody(BaseModel):
    """Body shape ``{url?, request}`` for UIs that include a gateway ``url`` field."""

    model_config = ConfigDict(json_schema_extra=_whois_nested_body_json_schema_extra)

    url: Optional[str] = Field(
        default=None,
        description="Ignored on this gateway (single BACnet/IP attachment).",
    )
    request: DeviceInstanceRange = Field(
        default_factory=DeviceInstanceRange,
        description="BACnet device instance range for Who-Is.",
    )


def install_openapi_whois_rest_example_patch(app) -> None:
    """Ensure OpenAPI example keeps ``url: null`` (some generators drop null keys)."""
    _prev = app.openapi

    def _combined_openapi():
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = _prev()
        try:
            rb = schema["paths"]["/bacnet/whois_range"]["post"]["requestBody"]["content"][
                "application/json"
            ]
            rb["example"] = {
                "url": None,
                "request": {"start_instance": 1, "end_instance": 3456799},
            }
        except KeyError:
            pass
        return schema

    app.openapi = _combined_openapi


def register_whois_nested_rest_routes(app) -> None:
    @app.post(
        "/bacnet/whois_range",
        tags=["BACnet"],
        summary="Who-Is range (nested url + request)",
        description=(
            'JSON body `{"url": null, "request": {"start_instance": 1, "end_instance": N}}` '
            "— `url` is ignored on this gateway. Prefer JSON-RPC `POST /client_whois_range` "
            "for automation."
        ),
        response_model=BaseResponse,
    )
    async def bacnet_whois_range_nested(body: WhoIsRangeNestedBody) -> BaseResponse:
        if body.url not in (None, ""):
            logger.debug("Ignoring url=%r on standalone gateway Who-Is", body.url)
        try:
            return await rpc_methods.client_whois_range(body.request)
        except JsonRpcBaseError as e:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": getattr(e, "CODE", None),
                    "message": getattr(e, "MESSAGE", str(e)),
                    "data": getattr(e, "data", None),
                },
            ) from e
