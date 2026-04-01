# rpc_app.py
import fastapi_jsonrpc as jsonrpc
from fastapi.responses import RedirectResponse
from bacpypes_server.rpc_auth import (
    install_openapi_bearer_for_swagger,
    install_rpc_auth_if_configured,
)
from bacpypes_server.rest_openfdd_aliases import (
    install_openapi_whois_rest_example_patch,
    register_openfdd_rest_aliases,
)
from bacpypes_server.rpc_methods import rpc

# Match Open-FDD API Swagger copy: same Authorize / Bearer story (see open_fdd/platform/api/main.py).
_SWAGGER_DESCRIPTION = (
    "When the server has RPC key auth enabled (BACNET_RPC_API_KEY set), **Try it out** will return 401 until you authorize: "
    "click **Authorize** at the top, paste your API key (e.g. from the **BACNET_RPC_API_KEY** environment variable, or when using Open-FDD from `stack/.env` → `OFDD_BACNET_SERVER_API_KEY`), "
    "then click Authorize and Close. "
    "After that, all requests from Swagger include the Bearer token."
)

rpc_api = jsonrpc.API(
    title="diy-bacnet-server",
    version="1.0",
    description=_SWAGGER_DESCRIPTION,
)
rpc_api.bind_entrypoint(rpc)

install_openapi_bearer_for_swagger(rpc_api)
install_rpc_auth_if_configured(rpc_api)

register_openfdd_rest_aliases(rpc_api)
install_openapi_whois_rest_example_patch(rpc_api)


# Optional: redirect base path
@rpc_api.router.get("/")
async def root_redirect():
    return RedirectResponse("/docs")
