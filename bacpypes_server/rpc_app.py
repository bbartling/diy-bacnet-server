# rpc_app.py
import os

import fastapi_jsonrpc as jsonrpc
from bacpypes_server.rpc_auth import (
    install_openapi_bearer_for_swagger,
    install_openapi_servers_url_from_env,
    install_rpc_auth_if_configured,
)
from bacpypes_server.rest_openfdd_aliases import (
    install_openapi_whois_rest_example_patch,
    register_openfdd_rest_aliases,
)
from bacpypes_server.modbus_routes import register_modbus_routes
from bacpypes_server.rpc_methods import rpc


def _openapi_docs_enabled() -> bool:
    return (os.environ.get("OFDD_ENABLE_OPENAPI_DOCS") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


_openapi = _openapi_docs_enabled()
_docs_url = "/docs" if _openapi else None
_redoc_url = "/redoc" if _openapi else None
_openapi_url = "/openapi.json" if _openapi else None
_rpc_desc = (
    "BACnet JSON-RPC gateway. Swagger is enabled on this deployment (HTTP lab); use Authorize with `BACNET_RPC_API_KEY` when set."
    if _openapi
    else "BACnet JSON-RPC gateway. Interactive docs are disabled on this deployment; send `Authorization: Bearer <BACNET_RPC_API_KEY>` when the key is set."
)

rpc_api = jsonrpc.API(
    title="diy-bacnet-server",
    version="1.0",
    description=_rpc_desc,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    openrpc_url=None,
)
rpc_api.bind_entrypoint(rpc)

install_openapi_bearer_for_swagger(rpc_api)
install_rpc_auth_if_configured(rpc_api)

register_openfdd_rest_aliases(rpc_api)
register_modbus_routes(rpc_api)
install_openapi_whois_rest_example_patch(rpc_api)
install_openapi_servers_url_from_env(rpc_api)


@rpc_api.router.get("/")
async def root_info():
    """Root info; Swagger may be enabled via OFDD_ENABLE_OPENAPI_DOCS (Open-FDD bootstrap)."""
    return {
        "service": "diy-bacnet-server",
        "message": (
            "JSON-RPC BACnet gateway. Swagger UI may be at /docs on this deployment."
            if _openapi
            else "JSON-RPC BACnet gateway. Interactive docs are disabled; use Open-FDD /bacnet-tools or POST JSON-RPC to this server."
        ),
    }
