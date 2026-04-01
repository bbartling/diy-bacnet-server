# mqtt_rpc_gateway.py — Optional MQTT command/ack/telemetry for JSON-RPC methods (generic broker).
# Inspired by request/response over pub/sub patterns; uses aiomqtt + same broker URL style as BACnet2MQTT.
# Gated by MQTT_RPC_GATEWAY_ENABLED. Not AWS-specific — works with Mosquitto and any MQTT 3.1.1 broker.
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Optional

from pydantic import ValidationError

logger = logging.getLogger("mqtt_rpc_gateway")

RECONNECT_DELAY_SEC = 5.0
DEFAULT_TOPIC_PREFIX = "diy-bacnet/gateway"
DEFAULT_TELEMETRY_INTERVAL_SEC = 0.0  # 0 = only retained telemetry/bridge, no periodic values

# Documented method names (mirror HTTP JSON-RPC); used for discovery payloads and tests.
MQTT_RPC_METHOD_NAMES: tuple[str, ...] = (
    "server_hello",
    "server_update_points",
    "server_read_commandable",
    "server_read_all_values",
    "client_read_property",
    "client_write_property",
    "client_read_multiple",
    "client_whois_range",
    "client_point_discovery",
    "client_supervisory_logic_checks",
    "client_read_point_priority_array",
    "client_whois_router_to_network",
)


def get_mqtt_rpc_gateway_config() -> Optional[dict]:
    """Return config dict or None if the MQTT RPC gateway is disabled."""
    if os.environ.get("MQTT_RPC_GATEWAY_ENABLED", "").strip().lower() not in ("1", "true", "yes"):
        return None
    url = os.environ.get("MQTT_RPC_BROKER_URL", "").strip() or os.environ.get(
        "MQTT_BROKER_URL", ""
    ).strip()
    if not url:
        logger.warning(
            "MQTT_RPC_GATEWAY_ENABLED set but MQTT_BROKER_URL (or MQTT_RPC_BROKER_URL) empty; "
            "MQTT RPC gateway disabled."
        )
        return None
    prefix = os.environ.get("MQTT_RPC_TOPIC_PREFIX", DEFAULT_TOPIC_PREFIX).strip().rstrip("/")
    if not prefix:
        prefix = DEFAULT_TOPIC_PREFIX
    try:
        telemetry_interval = float(
            os.environ.get("MQTT_RPC_TELEMETRY_INTERVAL_SEC", DEFAULT_TELEMETRY_INTERVAL_SEC)
        )
    except ValueError:
        telemetry_interval = DEFAULT_TELEMETRY_INTERVAL_SEC
    telemetry_interval = max(0.0, telemetry_interval)
    username = os.environ.get("MQTT_USER", "").strip() or None
    password = os.environ.get("MQTT_PASSWORD", "").strip() or None
    client_id = os.environ.get("MQTT_RPC_CLIENT_ID", "").strip() or None
    return {
        "broker_url": url,
        "topic_prefix": prefix,
        "telemetry_interval_sec": telemetry_interval,
        "username": username,
        "password": password,
        "client_id": client_id,
        "cmd_topic": f"{prefix}/cmd",
        "ack_topic": f"{prefix}/ack",
        "telemetry_bridge_topic": f"{prefix}/telemetry/bridge",
        "telemetry_status_topic": f"{prefix}/telemetry/status",
    }


def _parse_broker(url: str) -> tuple[str, int]:
    host, port = "localhost", 1883
    if "://" in url:
        _, rest = url.split("://", 1)
        rest = rest.split("/")[0]
        if ":" in rest:
            host, port_s = rest.rsplit(":", 1)
            try:
                port = int(port_s)
            except ValueError:
                pass
        else:
            host = rest
    else:
        h = url.split("/")[0]
        if ":" in h:
            host, port_s = h.rsplit(":", 1)
            try:
                port = int(port_s)
            except ValueError:
                pass
        else:
            host = h
    return host, port


def parse_mqtt_command_payload(raw: bytes) -> tuple[Optional[str], Optional[str], Optional[dict], Optional[str]]:
    """
    Parse MQTT command JSON.
    Returns (correlation_id, method, params, parse_error_message).
    On success parse_error_message is None.
    Accepts: method + params (JSON-RPC-shaped), optional correlation_id or id.
    """
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        return None, None, None, f"invalid_json: {e}"
    if not isinstance(data, dict):
        return None, None, None, "payload_must_be_object"
    corr = data.get("correlation_id")
    if corr is None:
        corr = data.get("id")
    corr_s = str(corr) if corr is not None else None
    method = data.get("method")
    if not method or not isinstance(method, str):
        return corr_s, None, None, "missing_or_invalid_method"
    params = data.get("params")
    if params is None:
        params = {}
    if not isinstance(params, dict):
        return corr_s, None, None, "params_must_be_object"
    return corr_s, method.strip(), params, None


def _normalize_result(result: Any) -> Any:
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


async def dispatch_mqtt_rpc(method: str, params: Optional[dict]) -> tuple[str, Any]:
    """
    Run one RPC method with the same semantics as HTTP JSON-RPC.
    Returns (status, payload) where status is 'ok' or 'error'.
    On error, payload is a dict with message/type/code/data.
    """
    from bacpypes_server import rpc_methods
    from bacpypes_server.models import (
        DeviceInstanceOnly,
        DeviceInstanceRange,
        PointUpdate,
        ReadMultiplePropertiesRequestWrapper,
        ReadPriorityArrayRequest,
        SingleReadRequest,
        WritePropertyRequest,
    )

    p = params or {}

    try:
        if method == "server_hello":
            out = rpc_methods.server_hello()
        elif method == "server_update_points":
            raw = p.get("update", p)
            upd = PointUpdate.model_validate(raw)
            out = rpc_methods.server_update_points(upd)
        elif method == "server_read_commandable":
            out = rpc_methods.server_read_commandable()
        elif method == "server_read_all_values":
            out = rpc_methods.server_read_all_values()
        elif method == "client_read_property":
            req = SingleReadRequest.model_validate(p.get("request", p))
            out = await rpc_methods.client_read_property(req)
        elif method == "client_write_property":
            req = WritePropertyRequest.model_validate(p.get("request", p))
            out = await rpc_methods.client_write_property(req)
        elif method == "client_read_multiple":
            req = ReadMultiplePropertiesRequestWrapper.model_validate(p.get("request", p))
            out = await rpc_methods.client_read_multiple(req)
        elif method == "client_whois_range":
            req = DeviceInstanceRange.model_validate(p.get("request", p))
            out = await rpc_methods.client_whois_range(req)
        elif method == "client_point_discovery":
            inst = DeviceInstanceOnly.model_validate(p.get("instance", p))
            out = await rpc_methods.client_point_discovery(inst)
        elif method == "client_supervisory_logic_checks":
            inst = DeviceInstanceOnly.model_validate(p.get("instance", p))
            out = await rpc_methods.client_supervisory_logic_checks(inst)
        elif method == "client_read_point_priority_array":
            req = ReadPriorityArrayRequest.model_validate(p.get("request", p))
            out = await rpc_methods.client_read_point_priority_array(req)
        elif method == "client_whois_router_to_network":
            out = await rpc_methods.client_whois_router_to_network()
        else:
            return "error", {
                "type": "unknown_method",
                "message": f"Unknown method: {method}",
                "known_methods": list(MQTT_RPC_METHOD_NAMES),
            }

        return "ok", _normalize_result(out)

    except ValidationError as e:
        return "error", {"type": "validation_error", "detail": e.errors()}
    except Exception as e:
        err: dict[str, Any] = {"type": type(e).__name__, "message": str(e)}
        if hasattr(e, "CODE"):
            err["code"] = getattr(e, "CODE")
        if hasattr(e, "MESSAGE"):
            err["message"] = getattr(e, "MESSAGE")
        if hasattr(e, "data") and getattr(e, "data") is not None:
            err["data"] = getattr(e, "data")
        logger.warning("MQTT RPC dispatch error for %s: %s", method, e)
        return "error", err


def build_ack_envelope(
    correlation_id: Optional[str],
    method: Optional[str],
    status: str,
    result: Any = None,
    error: Any = None,
) -> dict:
    env: dict[str, Any] = {
        "type": "mqtt_rpc_ack",
        "correlation_id": correlation_id or "unknown",
        "method": method,
        "ts_ms": int(time.time() * 1000),
        "status": status,
    }
    if status == "ok":
        env["result"] = result
    else:
        env["error"] = error
    return env


async def run_mqtt_rpc_gateway(
    point_map: dict,
    commandable_point_names: set,
    bacnet_instance_name: str = "BACnet",
    bacnet_instance_number: int = 0,
) -> None:
    """Connect to MQTT, subscribe to cmd topic, publish acks and optional telemetry."""
    config = get_mqtt_rpc_gateway_config()
    if not config:
        return

    try:
        import aiomqtt
    except ImportError:
        logger.error("aiomqtt not installed; MQTT RPC gateway disabled.")
        return

    from bacpypes_server.mqtt_bridge import build_bridge_devices_json

    host, port = _parse_broker(config["broker_url"])
    cmd_topic = config["cmd_topic"]
    ack_topic = config["ack_topic"]
    bridge_topic = config["telemetry_bridge_topic"]
    status_topic = config["telemetry_status_topic"]
    interval = config["telemetry_interval_sec"]

    client_kwargs: dict[str, Any] = {
        "hostname": host,
        "port": port,
        "username": config.get("username"),
        "password": config.get("password"),
    }
    if config.get("client_id"):
        client_kwargs["identifier"] = config["client_id"]

    while True:
        try:
            async with aiomqtt.Client(**client_kwargs) as client:
                bridge_payload = {
                    "schema": "diy-bacnet-mqtt-rpc/v1",
                    "bacnet_instance_name": bacnet_instance_name,
                    "bacnet_instance": bacnet_instance_number,
                    "methods": list(MQTT_RPC_METHOD_NAMES),
                    "cmd_topic": cmd_topic,
                    "ack_topic": ack_topic,
                    "telemetry_topics": {"bridge": bridge_topic, "status": status_topic},
                }
                await client.publish(
                    bridge_topic,
                    payload=json.dumps(bridge_payload, default=str),
                    retain=True,
                )
                await client.subscribe(cmd_topic, qos=1)
                logger.info(
                    "MQTT RPC gateway connected; cmd=%s ack=%s",
                    cmd_topic,
                    ack_topic,
                )

                async def publish_ack(payload: dict) -> None:
                    await client.publish(
                        ack_topic,
                        payload=json.dumps(payload, default=str),
                        qos=1,
                    )

                async def telemetry_tick() -> None:
                    devices = build_bridge_devices_json(point_map, commandable_point_names)
                    body = {
                        "ts_ms": int(time.time() * 1000),
                        "bacnet_instance": bacnet_instance_number,
                        "points_count": len(point_map),
                        "devices": devices,
                    }
                    await client.publish(
                        status_topic,
                        payload=json.dumps(body, default=str),
                        qos=0,
                    )

                tele_task: Optional[asyncio.Task] = None
                if interval > 0:
                    async def _loop() -> None:
                        while True:
                            await asyncio.sleep(interval)
                            try:
                                await telemetry_tick()
                            except asyncio.CancelledError:
                                raise
                            except Exception as e:
                                logger.debug("telemetry publish: %s", e)

                    tele_task = asyncio.create_task(_loop())

                try:
                    async for message in client.messages:
                        corr, method, params, parse_err = parse_mqtt_command_payload(
                            message.payload
                        )
                        if parse_err:
                            await publish_ack(
                                build_ack_envelope(
                                    corr,
                                    method,
                                    "error",
                                    error={"type": "parse_error", "message": parse_err},
                                )
                            )
                            continue
                        assert method is not None
                        status, body = await dispatch_mqtt_rpc(method, params)
                        if status == "ok":
                            await publish_ack(
                                build_ack_envelope(corr, method, "ok", result=body)
                            )
                        else:
                            await publish_ack(
                                build_ack_envelope(corr, method, "error", error=body)
                            )
                finally:
                    if tele_task is not None:
                        tele_task.cancel()
                        try:
                            await tele_task
                        except asyncio.CancelledError:
                            pass

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(
                "MQTT RPC gateway error: %s; reconnecting in %ss",
                e,
                RECONNECT_DELAY_SEC,
            )
            await asyncio.sleep(RECONNECT_DELAY_SEC)
