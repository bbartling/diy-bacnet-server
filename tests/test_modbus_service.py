"""Unit tests for Modbus decode and execute path (mocked client)."""

import pytest

from bacpypes_server.modbus_service import (
    ModbusServiceError,
    _decode_words,
    _apply_scale_offset,
    execute_modbus_read_request,
)


def test_decode_uint16():
    assert _decode_words([0x00FF], "uint16") == 255


def test_decode_int16_negative():
    v = _decode_words([0xFFFF], "int16")
    assert v == -1


def test_decode_float32_egauge_example():
    # 0x42f62a06 as IEEE BE float ≈ 123.08
    words = [0x42F6, 0x2A06]
    f = _decode_words(words, "float32")
    assert abs(f - 123.08) < 0.02


def test_decode_float32_requires_two_words():
    with pytest.raises(ModbusServiceError):
        _decode_words([1], "float32")


def test_apply_scale_offset():
    assert _apply_scale_offset(100.0, 0.1, None) == pytest.approx(10.0)
    assert _apply_scale_offset(10.0, None, 5.0) == pytest.approx(15.0)


class _FakeModbusClient:
    """Stub returning scripted words per (function, address)."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.opened = False

    def open(self):
        self.opened = True
        return True

    def close(self):
        pass

    def read_holding_registers(self, address, count):
        if address == 184:
            return [85]
        if address == 999:
            return False
        return [0, 0]

    def read_input_registers(self, address, count):
        if address == 500 and count == 2:
            return [0x42F6, 0x2A06]
        return False


def test_execute_modbus_read_request_mocked(monkeypatch):
    import bacpypes_server.modbus_service as ms

    monkeypatch.setattr(ms, "ModbusClient", _FakeModbusClient)

    payload = {
        "host": "10.0.0.5",
        "port": 502,
        "unit_id": 1,
        "timeout": 3.0,
        "registers": [
            {
                "address": 184,
                "count": 1,
                "function": "holding",
                "decode": "uint16",
                "label": "soc",
                "scale": None,
                "offset": None,
            },
            {
                "address": 500,
                "count": 2,
                "function": "input",
                "decode": "float32",
                "label": "v",
                "scale": None,
                "offset": None,
            },
            {
                "address": 999,
                "count": 1,
                "function": "holding",
                "decode": None,
                "label": None,
                "scale": None,
                "offset": None,
            },
        ],
    }

    out = execute_modbus_read_request(payload)
    assert out["ok"] is True
    assert out["host"] == "10.0.0.5"
    r0, r1, r2 = out["readings"]
    assert r0["success"] and r0["decoded"] == 85
    assert r1["success"] and abs(r1["decoded"] - 123.08) < 0.02
    assert r2["success"] is False
    assert r2["error"] == "read_failed_or_timeout"


def test_execute_too_many_ops():
    payload = {
        "host": "1.2.3.4",
        "port": 502,
        "unit_id": 1,
        "timeout": 3.0,
        "registers": [
            {"address": i, "count": 1, "function": "holding", "decode": None}
            for i in range(40)
        ],
    }
    with pytest.raises(ModbusServiceError):
        execute_modbus_read_request(payload)
