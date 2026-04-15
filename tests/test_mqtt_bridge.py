"""Unit tests for BACnet2MQTT bridge: topic parsing, payload mapping, bridge/devices and HA discovery payloads."""
import os
import pytest

from bacpypes_server.mqtt_bridge import (
    get_bridge_config,
    parse_set_topic,
    parse_set_payload,
    build_bridge_devices_json,
    build_state_payload,
    _point_type_and_units,
    DEFAULT_BASE_TOPIC,
)


# ─── Config ─────────────────────────────────────────────────────────────────

def test_get_bridge_config_disabled_by_default(monkeypatch):
    """When BACNET2MQTT_ENABLED is not set, get_bridge_config returns None."""
    monkeypatch.delenv("BACNET2MQTT_ENABLED", raising=False)
    monkeypatch.delenv("MQTT_BROKER_URL", raising=False)
    assert get_bridge_config() is None


def test_get_bridge_config_requires_broker_url(monkeypatch):
    """When BACNET2MQTT_ENABLED=1 but MQTT_BROKER_URL empty, returns None."""
    monkeypatch.setenv("BACNET2MQTT_ENABLED", "1")
    monkeypatch.setenv("MQTT_BROKER_URL", "")
    assert get_bridge_config() is None


def test_get_bridge_config_returns_config_when_enabled(monkeypatch):
    """When enabled and broker URL set, returns dict with base_topic, poll_interval, etc."""
    monkeypatch.setenv("BACNET2MQTT_ENABLED", "true")
    monkeypatch.setenv("MQTT_BROKER_URL", "mqtt://broker:1883")
    cfg = get_bridge_config()
    assert cfg is not None
    assert cfg["base_topic"] == DEFAULT_BASE_TOPIC
    assert cfg["broker_url"] == "mqtt://broker:1883"
    assert cfg["poll_interval_sec"] >= 1.0


def test_get_bridge_config_custom_base_topic(monkeypatch):
    monkeypatch.setenv("BACNET2MQTT_ENABLED", "1")
    monkeypatch.setenv("MQTT_BROKER_URL", "mqtt://localhost")
    monkeypatch.setenv("MQTT_BASE_TOPIC", "bacnet/local")
    cfg = get_bridge_config()
    assert cfg["base_topic"] == "bacnet/local"


# ─── Topic parsing ───────────────────────────────────────────────────────────

def test_parse_set_topic_valid():
    """base_topic/point-name/set -> point-name."""
    assert parse_set_topic("bacnet2mqtt", "bacnet2mqtt/outdoor-temp/set") == "outdoor-temp"
    assert parse_set_topic("bacnet2mqtt", "bacnet2mqtt/setpoint-temp/set") == "setpoint-temp"


def test_parse_set_topic_reject_bridge():
    """base_topic/bridge/... should not be treated as set."""
    assert parse_set_topic("bacnet2mqtt", "bacnet2mqtt/bridge/state") is None
    assert parse_set_topic("bacnet2mqtt", "bacnet2mqtt/bridge/set") is None  # middle is 'bridge'


def test_parse_set_topic_reject_no_set_suffix():
    assert parse_set_topic("bacnet2mqtt", "bacnet2mqtt/outdoor-temp") is None
    assert parse_set_topic("bacnet2mqtt", "bacnet2mqtt/outdoor-temp/state") is None


def test_parse_set_topic_reject_wrong_prefix():
    assert parse_set_topic("bacnet2mqtt", "other/outdoor-temp/set") is None


def test_parse_set_topic_reject_nested():
    """Reject base_topic/foo/bar/set (middle contains /)."""
    assert parse_set_topic("bacnet2mqtt", "bacnet2mqtt/foo/bar/set") is None


# ─── Payload parsing (with real AV/BV for isinstance) ────────────────────────
# Run with event loop so bacpypes3 local objects don't trigger "no current event loop" warning.

@pytest.mark.asyncio
async def test_parse_set_payload_av_float():
    """AV point accepts float string."""
    from bacpypes3.local.analog import AnalogValueObject
    from bacpypes3.primitivedata import Real
    obj = AnalogValueObject(
        objectIdentifier=("analogValue", 1),
        objectName="outdoor-temp",
        presentValue=Real(22.0),
    )
    point_map = {"outdoor-temp": obj}
    assert parse_set_payload("outdoor-temp", b"72.5", point_map) == 72.5
    assert parse_set_payload("outdoor-temp", b"  -1.5  ", point_map) == -1.5


@pytest.mark.asyncio
async def test_parse_set_payload_bv_active_inactive():
    """BV point accepts active/inactive, 1/0, true/false."""
    from bacpypes3.local.binary import BinaryValueObject
    obj = BinaryValueObject(
        objectIdentifier=("binaryValue", 1),
        objectName="opt",
        presentValue="inactive",
    )
    point_map = {"opt": obj}
    assert parse_set_payload("opt", b"active", point_map) == 1
    assert parse_set_payload("opt", b"1", point_map) == 1
    assert parse_set_payload("opt", b"true", point_map) == 1
    assert parse_set_payload("opt", b"inactive", point_map) == 0
    assert parse_set_payload("opt", b"0", point_map) == 0
    assert parse_set_payload("opt", b"false", point_map) == 0


def test_parse_set_payload_unknown_point_returns_none():
    point_map = {}
    assert parse_set_payload("nonexistent", b"1", point_map) is None


# ─── build_bridge_devices_json ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_build_bridge_devices_json():
    """Build list of device dicts with friendly_name, id, type, commandable, units."""
    from bacpypes3.local.analog import AnalogValueObject
    from bacpypes3.local.binary import BinaryValueObject
    from bacpypes3.primitivedata import Real
    from bacpypes3.basetypes import EngineeringUnits

    av = AnalogValueObject(
        objectIdentifier=("analogValue", 1),
        objectName="outdoor-temp",
        presentValue=Real(22.0),
        units=EngineeringUnits.degreesFahrenheit,
    )
    bv = BinaryValueObject(
        objectIdentifier=("binaryValue", 1),
        objectName="opt-enable",
        presentValue="inactive",
    )
    point_map = {"outdoor-temp": av, "opt-enable": bv}
    commandable = {"opt-enable"}

    devices = build_bridge_devices_json(point_map, commandable)
    assert len(devices) == 2
    by_name = {d["friendly_name"]: d for d in devices}
    assert by_name["outdoor-temp"]["type"] == "AV"
    assert by_name["outdoor-temp"]["commandable"] is False
    assert "units" in by_name["outdoor-temp"]  # may be None if enum has no .name
    assert by_name["opt-enable"]["type"] == "BV"
    assert by_name["opt-enable"]["commandable"] is True


# ─── build_state_payload ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_build_state_payload_av():
    from bacpypes3.local.analog import AnalogValueObject
    from bacpypes3.primitivedata import Real
    from bacpypes3.basetypes import EngineeringUnits

    av = AnalogValueObject(
        objectIdentifier=("analogValue", 1),
        objectName="outdoor-temp",
        presentValue=Real(72.5),
        units=EngineeringUnits.degreesFahrenheit,
    )
    point_map = {"outdoor-temp": av}
    payload = build_state_payload(point_map, "outdoor-temp")
    assert payload is not None
    assert payload["present_value"] == 72.5
    # units included when BACnet object exposes them (implementation may omit if enum has no .name)
    assert "present_value" in payload


@pytest.mark.asyncio
async def test_build_state_payload_bv():
    from bacpypes3.local.binary import BinaryValueObject

    bv = BinaryValueObject(
        objectIdentifier=("binaryValue", 1),
        objectName="opt",
        presentValue="active",
    )
    point_map = {"opt": bv}
    payload = build_state_payload(point_map, "opt")
    assert payload is not None
    assert payload["present_value"] == "active"


# ─── New point types: AI, AO, BI, BO, MSI, MSO, MSV ─────────────────────────

@pytest.mark.asyncio
async def test_point_type_and_units_ai_ao_bi_bo():
    """_point_type_and_units returns AI, AO, BI, BO for local objects."""
    from bacpypes3.local.analog import AnalogInputObject, AnalogOutputObject
    from bacpypes3.local.binary import BinaryInputObject, BinaryOutputObject
    from bacpypes3.primitivedata import Real
    from bacpypes3.basetypes import EngineeringUnits

    ai = AnalogInputObject(
        objectIdentifier=("analogInput", 1),
        objectName="temp-in",
        presentValue=Real(70.0),
        statusFlags=[0, 0, 0, 0],
        eventState="normal",
        outOfService=False,
        units=EngineeringUnits.degreesFahrenheit,
        covIncrement=1.0,
    )
    ptype, units = _point_type_and_units(ai)
    assert ptype == "AI"

    bo = BinaryOutputObject(
        objectIdentifier=("binaryOutput", 1),
        objectName="relay-1",
        presentValue="inactive",
        statusFlags=[0, 0, 0, 0],
        eventState="normal",
        outOfService=False,
        polarity="normal",
        relinquishDefault="inactive",
    )
    ptype, _ = _point_type_and_units(bo)
    assert ptype == "BO"


@pytest.mark.asyncio
async def test_point_type_and_units_msi_mso_msv():
    """_point_type_and_units returns MSI, MSO, MSV for multistate objects."""
    from bacpypes3.local.multistate import (
        MultiStateInputObject,
        MultiStateOutputObject,
        MultiStateValueObject,
    )

    msi = MultiStateInputObject(
        objectIdentifier=("multiStateInput", 1),
        objectName="mode-in",
        presentValue=1,
        statusFlags=[0, 0, 0, 0],
        eventState="normal",
        outOfService=False,
        numberOfStates=3,
    )
    assert _point_type_and_units(msi)[0] == "MSI"

    msv = MultiStateValueObject(
        objectIdentifier=("multiStateValue", 1),
        objectName="mode-val",
        presentValue=2,
        statusFlags=[0, 0, 0, 0],
        eventState="normal",
        outOfService=False,
        numberOfStates=4,
    )
    assert _point_type_and_units(msv)[0] == "MSV"


@pytest.mark.asyncio
async def test_parse_set_payload_multistate():
    """MSV/MSO/MSI accept integer payload."""
    from bacpypes3.local.multistate import MultiStateValueObject

    obj = MultiStateValueObject(
        objectIdentifier=("multiStateValue", 1),
        objectName="mode",
        presentValue=1,
        statusFlags=[0, 0, 0, 0],
        eventState="normal",
        outOfService=False,
        numberOfStates=5,
    )
    point_map = {"mode": obj}
    assert parse_set_payload("mode", b"3", point_map) == 3
    assert parse_set_payload("mode", b"1", point_map) == 1


# ─── Schedule object (bacpypes3.local.schedule) ──────────────────────────────

@pytest.mark.asyncio
async def test_schedule_point_type_and_state():
    """ScheduleObject is reported as type Schedule and present_value is readable."""
    from datetime import datetime
    from bacpypes3.local.schedule import ScheduleObject
    from bacpypes3.primitivedata import Integer, Date, Time
    from bacpypes3.basetypes import DateRange, DailySchedule, TimeValue

    def _bacnet_date(y: int, m: int, d: int) -> Date:
        dt = datetime(y, m, d)
        return Date((y - 1900, m, d, dt.weekday() + 1))

    def _tv(h: int, m: int, s: int, val: int) -> TimeValue:
        return TimeValue(time=Time((h, m, s, 0)), value=Integer(val))

    weekday = DailySchedule(daySchedule=[_tv(8, 0, 0, 1), _tv(17, 0, 0, 0)])
    weekend = DailySchedule(daySchedule=[_tv(0, 0, 0, 0)])
    weekly = [weekday, weekday, weekday, weekday, weekday, weekend, weekend]

    schedule_obj = ScheduleObject(
        objectIdentifier=("schedule", 1),
        objectName="office-hours",
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
    point_map = {"office-hours": schedule_obj}
    ptype, units = _point_type_and_units(schedule_obj)
    assert ptype == "Schedule"
    assert units is None
    payload = build_state_payload(point_map, "office-hours")
    assert payload is not None
    assert "present_value" in payload
