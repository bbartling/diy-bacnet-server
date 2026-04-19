# main.py
import asyncio
import logging
import argparse
import os

from bacpypes_server.env_features import (
    apply_openapi_docs_default_from_public,
    openapi_docs_enabled,
)
from bacpypes_server.server_utils import load_csv_and_create_objects, point_map, commandable_point_names
from bacpypes_server.client_utils import set_app
from bacpypes_server.mqtt_bridge import get_bridge_config, run_mqtt_bridge
from bacpypes_server.mqtt_rpc_gateway import get_mqtt_rpc_gateway_config, run_mqtt_rpc_gateway

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


class CustomArgumentParser(SimpleArgumentParser):
    def __init__(self):
        super().__init__()
        self.add_argument(
            "--public",
            action="store_true",
            help="If set, the server will listen on 0.0.0.0 instead of 127.0.0.1",
        )


async def main():
    args = CustomArgumentParser().parse_args()
    apply_openapi_docs_default_from_public(bool(args.public))

    try:
        bacnet_app = Application.from_args(args)
        set_app(bacnet_app)
        await load_csv_and_create_objects(bacnet_app)
        logger.info("BACnet application initialized.")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        return

    # Import after BACnet init succeeds; env default above makes /docs track --public unless overridden.
    from bacpypes_server.rpc_app import rpc_api

    # Choose host based on --public
    host = "0.0.0.0" if args.public else "127.0.0.1"

    # Start BACnet2MQTT bridge in background if enabled
    bridge_task = None
    mqtt_rpc_task = None
    if get_bridge_config() is not None:
        bridge_task = asyncio.create_task(
            run_mqtt_bridge(
                point_map,
                commandable_point_names,
                bacnet_instance_name=getattr(args, "name", "BACnet"),
                bacnet_instance_number=getattr(args, "instance", 0),
            )
        )
        logger.info("BACnet2MQTT bridge task started.")

    # Optional MQTT RPC gateway (cmd/ack/telemetry on a generic broker; see README)
    if get_mqtt_rpc_gateway_config() is not None:
        mqtt_rpc_task = asyncio.create_task(
            run_mqtt_rpc_gateway(
                point_map,
                commandable_point_names,
                bacnet_instance_name=getattr(args, "name", "BACnet"),
                bacnet_instance_number=getattr(args, "instance", 0),
            )
        )
        logger.info("MQTT RPC gateway task started.")

    # Start JSON-RPC server via uvicorn
    config = uvicorn.Config(app=rpc_api, host=host, port=8080, log_level="debug")
    server = uvicorn.Server(config)

    _docs_on = openapi_docs_enabled()
    if _docs_on:
        logger.info(
            f"JSON-RPC API ready at http://{host}:8080 (Swagger/OpenAPI at /docs)"
        )
    else:
        logger.info(
            f"JSON-RPC API ready at http://{host}:8080 (/docs off — use --public for Swagger on the LAN)"
        )
    try:
        await server.serve()
    finally:
        if bridge_task is not None:
            bridge_task.cancel()
            try:
                await bridge_task
            except asyncio.CancelledError:
                pass
        if mqtt_rpc_task is not None:
            mqtt_rpc_task.cancel()
            try:
                await mqtt_rpc_task
            except asyncio.CancelledError:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting gracefully.")
