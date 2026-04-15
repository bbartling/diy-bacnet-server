# mqtt_bridge.py — BACnet2MQTT bridge: local points <-> MQTT state/command topics.
# Gated by BACNET2MQTT_ENABLED.
import asyncio
import json
import logging
import os
from typing import Any, Optional

from bacpypes3.local.analog import (
    AnalogInputObject,
    AnalogOutputObject,
    AnalogValueObject,
)
from bacpypes3.local.binary import (
    BinaryInputObject,
    BinaryOutputObject,
    BinaryValueObject,
)
from bacpypes3.local.multistate import (
    MultiStateInputObject,
    MultiStateOutputObject,
    MultiStateValueObject,
)
from bacpypes3.local.schedule import ScheduleObject
from bacpypes3.json.util import atomic_encode

logger = logging.getLogger("mqtt_bridge")

# Defaults (overridden by env)
DEFAULT_BASE_TOPIC = "bacnet2mqtt"
DEFAULT_POLL_INTERVAL_SEC = 30.0
RECONNECT_DELAY_SEC = 5.0


def get_bridge_config() -> Optional[dict]:
    """Read bridge config from env. Returns None if bridge disabled."""
    if os.environ.get("BACNET2MQTT_ENABLED", "").strip().lower() not in ("1", "true", "yes"):
        return None
    url = os.environ.get("MQTT_BROKER_URL", "").strip()
    if not url:
        logger.warning("BACNET2MQTT_ENABLED set but MQTT_BROKER_URL empty; bridge disabled.")
        return None
    base_topic = os.environ.get("MQTT_BASE_TOPIC", DEFAULT_BASE_TOPIC).strip() or DEFAULT_BASE_TOPIC
    try:
        poll_interval = float(os.environ.get("MQTT_POLL_INTERVAL_SEC", DEFAULT_POLL_INTERVAL_SEC))
    except ValueError:
        poll_interval = DEFAULT_POLL_INTERVAL_SEC
    username = os.environ.get("MQTT_USER", "").strip() or None
    password = os.environ.get("MQTT_PASSWORD", "").strip() or None
    return {
        "broker_url": url,
        "base_topic": base_topic.rstrip("/"),
        "poll_interval_sec": max(1.0, poll_interval),
        "username": username,
        "password": password,
    }


def _point_type_and_units(obj: Any) -> tuple[str, Optional[str]]:
    """Return (point_type, units_str|None). point_type: AI, AO, AV, BI, BO, BV, MSI, MSO, MSV."""
    if isinstance(obj, AnalogInputObject):
        units = getattr(obj, "units", None)
        if units is not None and hasattr(units, "name"):
            return "AI", getattr(units, "name", str(units))
        return "AI", None
    if isinstance(obj, AnalogOutputObject):
        units = getattr(obj, "units", None)
        if units is not None and hasattr(units, "name"):
            return "AO", getattr(units, "name", str(units))
        return "AO", None
    if isinstance(obj, AnalogValueObject):
        units = getattr(obj, "units", None)
        if units is not None and hasattr(units, "name"):
            return "AV", getattr(units, "name", str(units))
        return "AV", None
    if isinstance(obj, BinaryInputObject):
        return "BI", None
    if isinstance(obj, BinaryOutputObject):
        return "BO", None
    if isinstance(obj, BinaryValueObject):
        return "BV", None
    if isinstance(obj, MultiStateInputObject):
        return "MSI", None
    if isinstance(obj, MultiStateOutputObject):
        return "MSO", None
    if isinstance(obj, MultiStateValueObject):
        return "MSV", None
    if isinstance(obj, ScheduleObject):
        return "Schedule", None
    return "AV", None  # fallback


def build_bridge_devices_json(
    point_map: dict,
    commandable_point_names: set,
) -> list[dict]:
    """Build list of device/point dicts for bridge/devices (friendly_name, id, type, commandable, units)."""
    devices = []
    for name, obj in point_map.items():
        ptype, units = _point_type_and_units(obj)
        devices.append({
            "friendly_name": name,
            "id": name,
            "type": ptype,
            "commandable": name in commandable_point_names,
            "units": units,
        })
    return devices


def parse_set_topic(base_topic: str, topic: str) -> Optional[str]:
    """If topic is base_topic/<name>/set, return name; else None. Ignore bridge sub-topics."""
    base = base_topic.rstrip("/")
    prefix = base + "/"
    suffix = "/set"
    if not topic.startswith(prefix) or not topic.endswith(suffix):
        return None
    middle = topic[len(prefix) : -len(suffix)]
    if not middle or "/" in middle or middle == "bridge":
        return None
    return middle


def parse_set_payload(
    point_name: str,
    payload: bytes,
    point_map: dict,
) -> Optional[Any]:
    """Parse MQTT set payload to value for PointUpdate. Returns None if invalid."""
    obj = point_map.get(point_name)
    if obj is None:
        return None
    try:
        raw = payload.decode("utf-8").strip()
    except Exception:
        return None
    if isinstance(obj, (BinaryValueObject, BinaryInputObject, BinaryOutputObject)):
        if raw.lower() in ("1", "true", "active", "on", "yes"):
            return 1
        if raw.lower() in ("0", "false", "inactive", "off", "no"):
            return 0
        try:
            return int(raw)
        except ValueError:
            return None
    if isinstance(obj, (AnalogValueObject, AnalogInputObject, AnalogOutputObject)):
        try:
            return float(raw)
        except ValueError:
            pass
        try:
            return json.loads(raw)
        except Exception:
            pass
        return None
    if isinstance(obj, (MultiStateValueObject, MultiStateInputObject, MultiStateOutputObject)):
        try:
            return int(raw)
        except ValueError:
            return None
    return None


def _read_point_value(obj: Any) -> Any:
    """Encode presentValue for JSON (float, or 'active'/'inactive')."""
    val = obj.presentValue
    # Unwrap AnyAtomic (e.g. Schedule presentValue) to inner Atomic
    if hasattr(val, "get_value") and callable(getattr(val, "get_value")):
        val = val.get_value()
    if hasattr(val, "encode"):
        return atomic_encode(val)
    return val if isinstance(val, (int, float)) else str(val)


def build_state_payload(point_map: dict, name: str) -> Optional[dict]:
    """Build JSON state for base_topic/<name>."""
    obj = point_map.get(name)
    if obj is None:
        return None
    ptype, units = _point_type_and_units(obj)
    value = _read_point_value(obj)
    out = {"present_value": value}
    if units:
        out["units"] = units
    return out


async def run_mqtt_bridge(
    point_map: dict,
    commandable_point_names: set,
    bacnet_instance_name: str = "BACnet",
    bacnet_instance_number: int = 0,
) -> None:
    """Run the MQTT bridge loop: connect, publish bridge/state and devices, subscribe, poll and handle set."""
    config = get_bridge_config()
    if not config:
        return

    from bacpypes_server.models import PointUpdate
    from bacpypes_server.rpc_methods import server_update_points

    base_topic = config["base_topic"]
    broker_url = config["broker_url"]
    poll_interval = config["poll_interval_sec"]

    # Parse broker URL (e.g. mqtt://host:1883)
    host = "localhost"
    port = 1883
    if "://" in broker_url:
        scheme, rest = broker_url.split("://", 1)
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
        host = broker_url.split("/")[0]
        if ":" in host:
            host, port_s = host.rsplit(":", 1)
            try:
                port = int(port_s)
            except ValueError:
                pass

    try:
        import aiomqtt
    except ImportError:
        logger.error("aiomqtt not installed; BACnet2MQTT bridge disabled. pip install aiomqtt")
        return

    bridge_state_off = json.dumps({"state": "offline"})
    bridge_state_on = json.dumps({"state": "online"})

    while True:
        try:
            async with aiomqtt.Client(
                hostname=host,
                port=port,
                username=config.get("username"),
                password=config.get("password"),
            ) as client:
                # LWT: last will topic (optional; aiomqtt may not expose will_set, so we publish offline on disconnect)
                state_topic = f"{base_topic}/bridge/state"
                info_topic = f"{base_topic}/bridge/info"
                devices_topic = f"{base_topic}/bridge/devices"

                await client.publish(state_topic, payload=bridge_state_on, retain=True)
                await client.publish(
                    info_topic,
                    payload=json.dumps({
                        "version": "1.0",
                        "bacnet_instance_name": bacnet_instance_name,
                        "bacnet_instance": bacnet_instance_number,
                    }),
                    retain=True,
                )
                devices_list = build_bridge_devices_json(point_map, commandable_point_names)
                await client.publish(
                    devices_topic,
                    payload=json.dumps(devices_list),
                    retain=True,
                )

                await client.subscribe(f"{base_topic}/#")
                logger.info("BACnet2MQTT bridge connected and subscribed to %s/#", base_topic)

                poll_task = asyncio.create_task(_poll_loop(client, base_topic, point_map, poll_interval))
                try:
                    async for message in client.messages:
                        topic = str(message.topic)
                        point_name = parse_set_topic(base_topic, topic)
                        if point_name is not None:
                            value = parse_set_payload(point_name, message.payload, point_map)
                            if value is not None:
                                try:
                                    server_update_points(PointUpdate(root={point_name: value}))
                                    # Publish updated state immediately
                                    state_payload = build_state_payload(point_map, point_name)
                                    if state_payload is not None:
                                        await client.publish(
                                            f"{base_topic}/{point_name}",
                                            payload=json.dumps(state_payload),
                                        )
                                except Exception as e:
                                    logger.warning("MQTT set failed for %s: %s", point_name, e)
                finally:
                    poll_task.cancel()
                    try:
                        await poll_task
                    except asyncio.CancelledError:
                        pass

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("BACnet2MQTT bridge error: %s; reconnecting in %ss", e, RECONNECT_DELAY_SEC)
            await asyncio.sleep(RECONNECT_DELAY_SEC)


async def _poll_loop(client: Any, base_topic: str, point_map: dict, interval: float) -> None:
    """Publish state for all points at interval."""
    while True:
        await asyncio.sleep(interval)
        for name in point_map:
            payload = build_state_payload(point_map, name)
            if payload is not None:
                try:
                    await client.publish(
                        f"{base_topic}/{name}",
                        payload=json.dumps(payload),
                    )
                except Exception as e:
                    logger.debug("Poll publish %s: %s", name, e)
