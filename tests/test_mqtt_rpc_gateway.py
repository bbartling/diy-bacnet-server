"""Unit tests for MQTT RPC gateway: config, payload parsing, dispatch, ack envelope."""

import asyncio
import json
import pytest

from bacpypes_server.mqtt_rpc_gateway import (
    MQTT_RPC_METHOD_NAMES,
    build_ack_envelope,
    dispatch_mqtt_rpc,
    get_mqtt_rpc_gateway_config,
    parse_mqtt_command_payload,
)
import bacpypes_server.rpc_methods as rpc_methods
from bacpypes3.local.schedule import ScheduleObject
from bacpypes3.basetypes import DateRange, DailySchedule, TimeValue
from bacpypes3.primitivedata import Date, Time, Integer


def test_gateway_config_disabled_by_default(monkeypatch):
    monkeypatch.delenv("MQTT_RPC_GATEWAY_ENABLED", raising=False)
    assert get_mqtt_rpc_gateway_config() is None


def test_gateway_config_disabled_without_broker(monkeypatch):
    monkeypatch.setenv("MQTT_RPC_GATEWAY_ENABLED", "true")
    monkeypatch.delenv("MQTT_BROKER_URL", raising=False)
    monkeypatch.delenv("MQTT_RPC_BROKER_URL", raising=False)
    assert get_mqtt_rpc_gateway_config() is None


def test_gateway_config_enabled(monkeypatch):
    monkeypatch.setenv("MQTT_RPC_GATEWAY_ENABLED", "1")
    monkeypatch.setenv("MQTT_BROKER_URL", "mqtt://broker.local:1883")
    monkeypatch.setenv("MQTT_RPC_TOPIC_PREFIX", "test/gw")
    monkeypatch.setenv("MQTT_RPC_TELEMETRY_INTERVAL_SEC", "60")
    cfg = get_mqtt_rpc_gateway_config()
    assert cfg is not None
    assert cfg["broker_url"] == "mqtt://broker.local:1883"
    assert cfg["topic_prefix"] == "test/gw"
    assert cfg["cmd_topic"] == "test/gw/cmd"
    assert cfg["ack_topic"] == "test/gw/ack"
    assert cfg["telemetry_interval_sec"] == 60.0


def test_gateway_uses_rpc_broker_url_override(monkeypatch):
    monkeypatch.setenv("MQTT_RPC_GATEWAY_ENABLED", "true")
    monkeypatch.setenv("MQTT_BROKER_URL", "mqtt://ignored:1883")
    monkeypatch.setenv("MQTT_RPC_BROKER_URL", "mqtt://override:8883")
    cfg = get_mqtt_rpc_gateway_config()
    assert cfg["broker_url"] == "mqtt://override:8883"


def test_parse_command_payload_ok():
    raw = json.dumps(
        {
            "correlation_id": "c1",
            "method": "server_hello",
            "params": {},
        }
    ).encode()
    corr, method, params, err = parse_mqtt_command_payload(raw)
    assert err is None
    assert corr == "c1"
    assert method == "server_hello"
    assert params == {}


def test_parse_command_payload_uses_id_as_correlation():
    raw = json.dumps({"id": 42, "method": "server_read_all_values", "params": {}}).encode()
    corr, method, params, err = parse_mqtt_command_payload(raw)
    assert err is None
    assert corr == "42"
    assert method == "server_read_all_values"


def test_parse_command_payload_invalid_json():
    corr, method, params, err = parse_mqtt_command_payload(b"not json")
    assert err is not None
    assert method is None


def test_parse_command_payload_missing_method():
    raw = json.dumps({"params": {}}).encode()
    corr, method, params, err = parse_mqtt_command_payload(raw)
    assert err == "missing_or_invalid_method"


def test_build_ack_envelope_ok():
    env = build_ack_envelope("x", "server_hello", "ok", result={"message": "hi"})
    assert env["type"] == "mqtt_rpc_ack"
    assert env["correlation_id"] == "x"
    assert env["method"] == "server_hello"
    assert env["status"] == "ok"
    assert env["result"] == {"message": "hi"}
    assert "error" not in env


def test_build_ack_envelope_error():
    env = build_ack_envelope("y", "bad", "error", error={"type": "x"})
    assert env["status"] == "error"
    assert env["error"] == {"type": "x"}
    assert "result" not in env


def test_dispatch_server_hello():
    status, body = asyncio.run(dispatch_mqtt_rpc("server_hello", {}))
    assert status == "ok"
    assert "message" in body


def test_dispatch_unknown_method():
    status, body = asyncio.run(dispatch_mqtt_rpc("not_a_real_method", {}))
    assert status == "error"
    assert body["type"] == "unknown_method"
    assert "not_a_real_method" in body["message"]


def test_dispatch_validation_error():
    status, body = asyncio.run(
        dispatch_mqtt_rpc(
            "server_update_points",
            {"update": "not-a-dict"},
        )
    )
    assert status == "error"
    assert body["type"] == "validation_error"


def test_dispatch_server_read_all_values():
    status, body = asyncio.run(dispatch_mqtt_rpc("server_read_all_values", {}))
    assert status == "ok"
    assert isinstance(body, dict)


def _bacnet_date(y: int, m: int, d: int) -> Date:
    import datetime as _dt

    dt = _dt.datetime(y, m, d)
    return Date((y - 1900, m, d, dt.weekday() + 1))


def _tv(h: int, m: int, s: int, val: int) -> TimeValue:
    return TimeValue(time=Time((h, m, s, 0)), value=Integer(val))


def _build_schedule_object(name: str = "occupancy-schedule") -> ScheduleObject:
    weekday = DailySchedule(daySchedule=[_tv(8, 0, 0, 1), _tv(17, 0, 0, 0)])
    weekend = DailySchedule(daySchedule=[_tv(0, 0, 0, 0)])
    weekly = [weekday, weekday, weekday, weekday, weekday, weekend, weekend]
    return ScheduleObject(
        objectIdentifier=("schedule", 1),
        objectName=name,
        presentValue=Integer(0),
        effectivePeriod=DateRange(
            startDate=_bacnet_date(2024, 1, 1),
            endDate=_bacnet_date(2030, 12, 31),
        ),
        weeklySchedule=weekly,
        exceptionSchedule=[],
        scheduleDefault=Integer(0),
        listOfObjectPropertyReferences=[],
        priorityForWriting=1,
        statusFlags=[0, 0, 0, 0],
        reliability="noFaultDetected",
        outOfService=False,
    )


@pytest.mark.asyncio
async def test_dispatch_server_read_schedule():
    rpc_methods.point_map["occupancy-schedule"] = _build_schedule_object()
    status, body = await dispatch_mqtt_rpc(
        "server_read_schedule", {"request": {"name": "occupancy-schedule"}}
    )
    assert status == "ok"
    assert body["status"] == "ok"
    assert body["schedule"]["object_name"] == "occupancy-schedule"


@pytest.mark.asyncio
async def test_dispatch_server_update_schedule():
    rpc_methods.point_map["occupancy-schedule"] = _build_schedule_object()
    status, body = await dispatch_mqtt_rpc(
        "server_update_schedule",
        {
            "update": {
                "name": "occupancy-schedule",
                "schedule_default": 1,
            }
        },
    )
    assert status == "ok"
    assert body["status"] == "updated"
    assert body["changed"]["schedule_default"] == 1


def test_method_names_cover_rpc_surface():
    assert "client_whois_range" in MQTT_RPC_METHOD_NAMES
    assert "client_read_property" in MQTT_RPC_METHOD_NAMES
    assert "server_read_schedule" in MQTT_RPC_METHOD_NAMES
    assert "server_update_schedule" in MQTT_RPC_METHOD_NAMES
    assert len(MQTT_RPC_METHOD_NAMES) >= 12
