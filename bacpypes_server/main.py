# main.py
import asyncio
import logging

from web_app import api_app, start_api_server
from server_utils import load_csv_and_create_objects, point_map

from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.ipv4.app import Application
from bacpypes3.debugging import bacpypes_debugging, ModuleLogger
from client_utils import set_app

"""
python3 bacpypes_server/main.py --name BensServer --instance 123456 --debug
"""

# Set global logging configuration
logging.basicConfig(
    level=logging.DEBUG,  # or logging.INFO for less verbosity
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Optional: suppress noisy third-party loggers
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
    except Exception as e:
        logger.error(f"Startup error: {e}")
        return

    asyncio.create_task(start_api_server())
    logger.info("FastAPI REST API started at http://localhost:8080/docs")
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting.")
