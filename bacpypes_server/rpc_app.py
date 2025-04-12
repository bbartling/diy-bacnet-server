# rpc_app.py
import fastapi_jsonrpc as jsonrpc
from fastapi.responses import RedirectResponse
from rpc_methods import rpc

rpc_api = jsonrpc.API()
rpc_api.bind_entrypoint(rpc)


# Optional: redirect base path
@rpc_api.router.get("/")
async def root_redirect():
    return RedirectResponse("/docs")
