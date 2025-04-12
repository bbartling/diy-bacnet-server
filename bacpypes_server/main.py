# main.py
import asyncio
import logging

from rpc_app import rpc_api
from server_utils import load_csv_and_create_objects
from client_utils import set_app

from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.ipv4.app import Application
from bacpypes3.debugging import ModuleLogger

import uvicorn

"""
Run with:
python3 main.py --name BensServer --instance 123456 --debug
"""

# ──────── LOGGING SETUP ────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

_debug = 1
logger = ModuleLogger(globals())


async def main():
    args = SimpleArgumentParser().parse_args()

    try:
        bacnet_app = Application.from_args(args)
        set_app(bacnet_app)
        await load_csv_and_create_objects(bacnet_app)
        logger.info("BACnet application initialized.")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        return

    # Start JSON-RPC server via uvicorn
    config = uvicorn.Config(app=rpc_api, host="0.0.0.0", port=8080, log_level="debug")
    server = uvicorn.Server(config)

    logger.info("JSON-RPC API ready at http://localhost:8080/docs")
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting gracefully.")
