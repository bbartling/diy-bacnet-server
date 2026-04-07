"""
Synchronous Modbus TCP reads via pyModbusTCP (use asyncio.to_thread from FastAPI).

Generic utility-meter / eGauge-style use: pass register addresses, counts, and optional
decoding (uint16, float32, …). Addressing is passed through as the device expects
(0-based vs 1-based is device-specific — document in operator guides).
"""

from __future__ import annotations

import struct
from typing import Any, Literal, Optional

from pyModbusTCP.client import ModbusClient

ModbusFunction = Literal["holding", "input"]
DecodeKind = Optional[
    Literal["raw", "uint16", "int16", "uint32", "int32", "float32"]
]

# Modbus PDU limits (defensive caps for API safety)
MAX_REGS_PER_OPERATION = 125
MAX_OPERATIONS_PER_REQUEST = 32


class ModbusServiceError(ValueError):
    """Invalid request or device read failure (wrapped as HTTP 400 in routes)."""


def _decode_words(words: list[int], decode: DecodeKind) -> Any:
    if decode is None or decode == "raw":
        return None
    if not words:
        raise ModbusServiceError("No register words to decode")
    if decode == "uint16":
        if len(words) < 1:
            raise ModbusServiceError("uint16 needs count >= 1")
        return int(words[0]) & 0xFFFF
    if decode == "int16":
        if len(words) < 1:
            raise ModbusServiceError("int16 needs count >= 1")
        return struct.unpack(">h", struct.pack(">H", int(words[0]) & 0xFFFF))[0]
    if decode in ("uint32", "int32", "float32"):
        if len(words) < 2:
            raise ModbusServiceError(f"{decode} needs count >= 2 (two 16-bit words)")
        hi, lo = int(words[0]) & 0xFFFF, int(words[1]) & 0xFFFF
        packed = struct.pack(">HH", hi, lo)
        if decode == "uint32":
            return struct.unpack(">I", packed)[0]
        if decode == "int32":
            return struct.unpack(">i", packed)[0]
        return struct.unpack(">f", packed)[0]
    raise ModbusServiceError(f"Unknown decode kind: {decode}")


def _apply_scale_offset(value: Any, scale: Optional[float], offset: Optional[float]) -> Any:
    if value is None:
        return None
    if not isinstance(value, (int, float)):
        return value
    out = float(value)
    if scale is not None:
        out *= scale
    if offset is not None:
        out += offset
    if isinstance(value, int) and scale is None and offset is None:
        return value
    return out


def execute_modbus_read_request(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Run one Modbus TCP session with multiple read operations (same host/port/unit).

    ``payload`` matches ModbusReadRequestBody.model_dump() from routes.
    """
    host = payload["host"]
    port = int(payload["port"])
    unit_id = int(payload["unit_id"])
    timeout = float(payload["timeout"])
    registers = payload["registers"]

    if len(registers) > MAX_OPERATIONS_PER_REQUEST:
        raise ModbusServiceError(
            f"At most {MAX_OPERATIONS_PER_REQUEST} register operations per request"
        )

    client = ModbusClient(
        host=host,
        port=port,
        unit_id=unit_id,
        timeout=timeout,
        auto_open=True,
        auto_close=True,
    )

    readings: list[dict[str, Any]] = []

    for spec in registers:
        address = int(spec["address"])
        count = int(spec["count"])
        fn: ModbusFunction = spec["function"]
        decode: DecodeKind = spec.get("decode")
        scale = spec.get("scale")
        offset = spec.get("offset")
        label = spec.get("label")

        if count < 1 or count > MAX_REGS_PER_OPERATION:
            raise ModbusServiceError(
                f"count must be 1..{MAX_REGS_PER_OPERATION} (got {count})"
            )

        if decode in ("uint16", "int16") and count < 1:
            raise ModbusServiceError("decode requires sufficient count")
        if decode in ("uint32", "int32", "float32") and count < 2:
            raise ModbusServiceError(
                f"decode={decode} requires count >= 2 (got {count})"
            )

        try:
            if fn == "holding":
                words = client.read_holding_registers(address, count)
            elif fn == "input":
                words = client.read_input_registers(address, count)
            else:
                raise ModbusServiceError(f"Invalid function: {fn}")
        except Exception as e:  # pragma: no cover - pyModbusTCP network errors
            readings.append(
                {
                    "address": address,
                    "function": fn,
                    "count": count,
                    "success": False,
                    "words": None,
                    "decoded": None,
                    "label": label,
                    "error": f"modbus_exception: {e}",
                }
            )
            continue

        if words is False or words is None:
            readings.append(
                {
                    "address": address,
                    "function": fn,
                    "count": count,
                    "success": False,
                    "words": None,
                    "decoded": None,
                    "label": label,
                    "error": "read_failed_or_timeout",
                }
            )
            continue

        words_list = [int(w) & 0xFFFF for w in words]
        try:
            decoded = _decode_words(words_list, decode)
            decoded = _apply_scale_offset(decoded, scale, offset)
        except ModbusServiceError as e:
            readings.append(
                {
                    "address": address,
                    "function": fn,
                    "count": count,
                    "success": True,
                    "words": words_list,
                    "decoded": None,
                    "label": label,
                    "error": str(e),
                }
            )
            continue

        readings.append(
            {
                "address": address,
                "function": fn,
                "count": count,
                "success": True,
                "words": words_list,
                "decoded": decoded,
                "label": label,
                "error": None,
            }
        )

    return {
        "ok": True,
        "host": host,
        "port": port,
        "unit_id": unit_id,
        "timeout": timeout,
        "readings": readings,
    }
