"""Pydantic request/response model validation — no BACnet stack required."""

import pytest
from pydantic import ValidationError

from bacpypes_server.models import (
    DeviceInstanceRange,
    DeviceInstanceOnly,
    SingleReadRequest,
    WritePropertyRequest,
    ReadMultiplePropertiesRequest,
    ReadMultiplePropertiesRequestWrapper,
    ReadPriorityArrayRequest,
    parse_object_identifier_parts,
)


def test_device_instance_range_valid():
    r = DeviceInstanceRange(start_instance=1, end_instance=3456799)
    assert r.start_instance == 1
    assert r.end_instance == 3456799


def test_device_instance_range_defaults_match_open_fdd_whois():
    """Same defaults as open_fdd/platform/api/bacnet.py WhoIsRequestRange."""
    r = DeviceInstanceRange()
    assert r.start_instance == 1
    assert r.end_instance == 3456799


def test_device_instance_range_invalid_bounds():
    with pytest.raises(ValidationError):
        DeviceInstanceRange(start_instance=1, end_instance=99999999)


def test_device_instance_only_valid():
    r = DeviceInstanceOnly(device_instance=3456789)
    assert r.device_instance == 3456789


def test_single_read_request_valid():
    r = SingleReadRequest(
        device_instance=3456789,
        object_identifier="analog-value,1",
        property_identifier="present-value",
    )
    assert r.object_identifier == "analog-value,1"
    assert r.property_identifier == "present-value"


def test_single_read_request_default_property():
    r = SingleReadRequest(device_instance=1, object_identifier="analog-input,1")
    assert r.property_identifier == "present-value"


def test_single_read_request_invalid_object_identifier():
    with pytest.raises(ValidationError):
        SingleReadRequest(
            device_instance=1,
            object_identifier="no-comma",
        )
    with pytest.raises(ValidationError):
        SingleReadRequest(
            device_instance=1,
            object_identifier="invalid-type,1",
        )


def test_write_property_request_valid():
    r = WritePropertyRequest(
        device_instance=3456789,
        object_identifier="analog-value,2",
        property_identifier="present-value",
        value=55.0,
        priority=8,
    )
    assert r.value == 55.0
    assert r.priority == 8


def test_write_property_request_release_null():
    r = WritePropertyRequest(
        device_instance=3456789,
        object_identifier="analog-value,2",
        property_identifier="present-value",
        value="null",
        priority=8,
    )
    assert r.value == "null"
    assert r.priority == 8


def test_write_property_request_invalid_property():
    with pytest.raises(ValidationError):
        WritePropertyRequest(
            device_instance=1,
            object_identifier="analog-value,1",
            property_identifier="not-a-property",
            value=1.0,
        )


def test_read_multiple_request_valid():
    r = ReadMultiplePropertiesRequest(
        object_identifier="analog-input,1",
        property_identifier="present-value",
    )
    assert r.object_identifier == "analog-input,1"


def test_read_multiple_wrapper_valid():
    r = ReadMultiplePropertiesRequestWrapper(
        device_instance=3456789,
        requests=[
            ReadMultiplePropertiesRequest(
                object_identifier="analog-input,1",
                property_identifier="present-value",
            ),
            ReadMultiplePropertiesRequest(
                object_identifier="analog-value,2",
                property_identifier="present-value",
            ),
        ],
    )
    assert len(r.requests) == 2
    assert r.requests[0].object_identifier == "analog-input,1"


def test_read_priority_array_request_valid():
    r = ReadPriorityArrayRequest(
        device_instance=3456789,
        object_identifier="analog-output,1",
    )
    assert r.object_identifier == "analog-output,1"


def test_bacpypes3_object_identifier_formats():
    """BACpypes3 uses ObjectType enum; standard hyphenated names (e.g. analog-value) work. No app-side conversion needed."""
    # Standard hyphenated format (BACnet / bacpypes3 recommended)
    typ, inst = parse_object_identifier_parts("analog-value,1")
    assert typ == "analog-value"
    assert inst == 1
    typ, inst = parse_object_identifier_parts("binary-output,1")
    assert typ == "binary-output"
    assert inst == 1
    # ObjectIdentifier from parsed parts (bacpypes3 accepts tuple from ObjectType)
    from bacpypes3.primitivedata import ObjectIdentifier

    oid = ObjectIdentifier(("analog-value", 1))
    assert oid is not None
    # String form: bacpypes3 accepts "object-type,instance" (hyphenated)
    oid_from_str = ObjectIdentifier("analog-value,1")
    assert oid_from_str is not None
