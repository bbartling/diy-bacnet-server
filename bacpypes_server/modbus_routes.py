"""
REST API for Modbus TCP client reads (utility meters, eGauge, inverters, etc.).

pyModbusTCP is synchronous; handlers use asyncio.to_thread so the event loop stays responsive.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Literal, Optional

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from bacpypes_server.modbus_service import ModbusServiceError, execute_modbus_read_request

logger = logging.getLogger("modbus_routes")

DecodeLiteral = Literal["raw", "uint16", "int16", "uint32", "int32", "float32"]
FunctionLiteral = Literal["holding", "input"]


class ModbusRegisterOp(BaseModel):
    """One Modbus read (function 03 holding or 04 input)."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "address": 500,
                    "count": 2,
                    "function": "input",
                    "decode": "float32",
                    "label": "L1 RMS voltage (V)",
                },
                {"address": 184, "count": 1, "function": "holding", "decode": "uint16"},
            ]
        }
    )

    address: int = Field(..., ge=0, le=65535)
    count: int = Field(default=1, ge=1, le=125)
    function: FunctionLiteral = Field(
        default="holding",
        description="Modbus function: 03 holding registers or 04 input registers.",
    )
    decode: Optional[DecodeLiteral] = Field(
        default=None,
        description=(
            "Optional interpretation of returned words (big-endian; first word = high 16 bits). "
            "float32 / int32 / uint32 need count >= 2. "
            "Use null for raw word list only."
        ),
    )
    scale: Optional[float] = Field(
        default=None,
        description="Multiply decoded numeric value by this factor (e.g. 0.1 for 0.1 V units).",
    )
    offset: Optional[float] = Field(
        default=None,
        description="Add to decoded value after scale (engineering unit offset).",
    )
    label: Optional[str] = Field(
        default=None,
        description="Optional human-readable tag (e.g. 'Grid L1-N V'); echoed in the response.",
    )

    @model_validator(mode="after")
    def decode_needs_word_count(self) -> ModbusRegisterOp:
        if self.decode in ("float32", "uint32", "int32") and self.count < 2:
            raise ValueError(
                f"decode={self.decode!r} requires count >= 2 (two 16-bit Modbus words)"
            )
        return self


class ModbusReadRequestBody(BaseModel):
    """Batch Modbus TCP reads over one connection."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "host": "10.200.200.170",
                "port": 502,
                "unit_id": 1,
                "timeout": 5.0,
                "registers": [
                    {
                        "address": 184,
                        "count": 1,
                        "function": "holding",
                        "decode": "uint16",
                        "label": "Battery SoC %",
                    },
                    {
                        "address": 500,
                        "count": 2,
                        "function": "input",
                        "decode": "float32",
                        "scale": 1.0,
                        "label": "L1 voltage (example)",
                    },
                ],
            }
        }
    )

    host: str = Field(..., description="Modbus TCP host (IP or DNS).")
    port: int = Field(default=502, ge=1, le=65535)
    unit_id: int = Field(default=1, ge=0, le=255)
    timeout: float = Field(default=5.0, ge=0.5, le=60.0)
    registers: list[ModbusRegisterOp] = Field(
        ...,
        min_length=1,
        max_length=32,
    )

    @field_validator("host")
    @classmethod
    def strip_host(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("host must be non-empty")
        return v


def register_modbus_routes(app) -> None:
    """Attach Modbus routes to the FastAPI / jsonrpc API instance."""

    @app.post(
        "/modbus/read_registers",
        tags=["Modbus TCP"],
        summary="Read holding/input registers over Modbus TCP",
        description=(
            "Generic Modbus TCP client for **utility metering** and similar gear (eGauge, inverters, "
            "EMS gateways). Each request opens one TCP connection, runs serial reads, and returns raw "
            "16-bit words plus optional decoded scalars (``uint16``, ``float32``, …). "
            "**Addressing** is device-specific (some vendors document 1-based addresses in manuals but "
            "expose 0-based on the wire — use the address your device map or CSV specifies). "
            "eGauge and others may use **input registers** (function 04) for meter map data — set "
            "``function`` to ``input`` for those blocks."
        ),
    )
    async def modbus_read_registers(body: ModbusReadRequestBody) -> dict:
        try:
            payload = body.model_dump()
            return await asyncio.to_thread(execute_modbus_read_request, payload)
        except ModbusServiceError as e:
            logger.warning("Modbus read validation error: %s", e)
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:  # pragma: no cover - defensive
            logger.exception("Modbus read failed")
            raise HTTPException(
                status_code=502,
                detail=f"modbus_tcp_error: {e}",
            ) from e
