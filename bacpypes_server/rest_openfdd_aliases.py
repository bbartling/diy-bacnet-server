# rest_openfdd_aliases.py — REST routes whose bodies match Open-FDD proxy Swagger (optional parity).
# JSON-RPC paths (e.g. POST /client_whois_range) are unchanged; this is for humans comparing UIs.
from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException
from fastapi_jsonrpc import BaseError as JsonRpcBaseError
from pydantic import BaseModel, ConfigDict, Field

from bacpypes_server.models import BaseResponse, DeviceInstanceRange
from bacpypes_server import rpc_methods

logger = logging.getLogger("rest_openfdd_aliases")


def _openfdd_whois_body_json_schema_extra(schema: dict) -> None:
    """url before request; start_instance before end_instance inside example.request."""
    props = schema.get("properties") or {}
    if "url" in props and "request" in props:
        schema["properties"] = {"url": props["url"], "request": props["request"]}
    schema["example"] = {
        "url": None,
        "request": {"start_instance": 1, "end_instance": 3456799},
    }


class OpenFddWhoIsBody(BaseModel):
    """Same JSON shape as Open-FDD ``POST /bacnet/whois_range``. ``url`` is ignored here (single gateway)."""

    model_config = ConfigDict(json_schema_extra=_openfdd_whois_body_json_schema_extra)

    url: Optional[str] = Field(
        default=None,
        description="Ignored on this gateway; Open-FDD uses this to pick a remote gateway URL.",
    )
    request: DeviceInstanceRange = Field(
        default_factory=DeviceInstanceRange,
        description="BACnet device instance range for Who-Is.",
    )


_OPENFDD_WHOIS_EXAMPLE = {
    "url": None,
    "request": {"start_instance": 1, "end_instance": 3456799},
}


def install_openapi_whois_rest_example_patch(app) -> None:
    """Force REST Who-Is example to match Open-FDD (FastAPI drops null keys from examples)."""
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


def register_openfdd_rest_aliases(app) -> None:
    @app.post(
        "/bacnet/whois_range",
        tags=["BACnet"],
        summary="Who-Is range (Open-FDD-compatible body)",
        description=(
            "Same request JSON as **Open-FDD** `POST /bacnet/whois_range`: `{ \"url\", \"request\" }`. "
            "The `url` field is ignored on diy-bacnet-server. "
            "For machine clients you can still use JSON-RPC `POST /client_whois_range`."
        ),
        response_model=BaseResponse,
    )
    async def bacnet_whois_range_openfdd_shape(body: OpenFddWhoIsBody) -> BaseResponse:
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
