# rpc_app.py
import os

import fastapi_jsonrpc as jsonrpc
from bacpypes_server.env_features import openapi_docs_enabled
from bacpypes_server.rpc_auth import (
    install_openapi_bearer_for_swagger,
    install_openapi_servers_url_from_env,
    install_rpc_auth_if_configured,
)
from bacpypes_server.rest_whois_nested import (
    install_openapi_whois_rest_example_patch,
    register_whois_nested_rest_routes,
)
from bacpypes_server.modbus_routes import register_modbus_routes
from bacpypes_server.rpc_methods import CLIENT_TAG, SERVER_TAG, rpc


_openapi = openapi_docs_enabled()
_docs_url = "/docs" if _openapi else None
_redoc_url = "/redoc" if _openapi else None
_openapi_url = "/openapi.json" if _openapi else None
_rpc_desc = (
    "BACnet JSON-RPC gateway. Swagger is enabled; use Authorize with `BACNET_RPC_API_KEY` when set."
    if _openapi
    else "BACnet JSON-RPC gateway. Interactive docs are disabled; send `Authorization: Bearer <BACNET_RPC_API_KEY>` when the key is set."
)

rpc_api = jsonrpc.API(
    title="diy-bacnet-server",
    version="1.0",
    description=_rpc_desc,
    openapi_tags=[
        {"name": SERVER_TAG, "description": "Server object-map RPC endpoints (read/update local hosted points)."},
        {"name": CLIENT_TAG, "description": "BACnet network client RPC endpoints (whois/read/write/discovery)."},
    ],
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
    openrpc_url=None,
)
rpc_api.bind_entrypoint(rpc)

install_openapi_bearer_for_swagger(rpc_api)
install_rpc_auth_if_configured(rpc_api)

register_whois_nested_rest_routes(rpc_api)
register_modbus_routes(rpc_api)
install_openapi_whois_rest_example_patch(rpc_api)
install_openapi_servers_url_from_env(rpc_api)


@rpc_api.router.get("/")
async def root_info():
    """Default discovery route points users to server_hello RPC."""
    return {
        "service": "diy-bacnet-server",
        "default_rpc_route": "/server_hello",
        "message": "Use POST /server_hello as the default health/discovery RPC route.",
    }
