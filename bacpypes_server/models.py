from pydantic import (
    ConfigDict,
    RootModel,
    BaseModel,
    StrictBool,
    conint,
    confloat,
    Field,
    ValidationError,
    field_validator,
)
from typing import Dict, Union, Optional, List

from bacpypes3.primitivedata import PropertyIdentifier, ObjectType
from fastapi import HTTPException
import math


def parse_object_identifier_parts(value: str) -> tuple[str, int]:
    """
    Parse 'objectType,instanceNumber' and return (object_type, instance).
    Raises ValueError if format or values are invalid.
    """
    if "," not in value:
        raise ValueError("Must be in the format objectType,instanceNumber")
    object_type, instance_str = value.split(",", 1)
    object_type = object_type.strip()
    if object_type not in ObjectType._enum_map:
        raise ValueError(f"Invalid object type: {object_type}")
    try:
        instance = int(instance_str.strip())
    except ValueError:
        raise ValueError("Instance number must be an integer")
    if not (0 <= instance <= 4194303):
        raise ValueError("Instance out of range")
    return object_type, instance


class PointUpdate(
    RootModel[Dict[str, Union[conint(strict=True), confloat(strict=True), StrictBool]]]
):
    pass


def nan_or_inf_check(encoded_value):
    if isinstance(encoded_value, float):
        if math.isnan(encoded_value):
            return "NaN"
        elif math.isinf(encoded_value):
            return "Inf" if encoded_value > 0 else "-Inf"
    return encoded_value


class BaseResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class PriorityArrayResponse(BaseModel):
    priority_level: int
    type: str
    value: Union[str, float, None]


class SupervisorySummary(BaseModel):
    device_id: int
    address: Optional[str]
    points: List[dict]  # You could break this into another Pydantic model if desired
    summary: Dict[str, int]


class DeviceInstanceOnly(BaseModel):
    model_config = ConfigDict(json_schema_extra={"example": {"device_instance": 987654}})

    device_instance: conint(ge=0, le=4194303) = Field(
        ..., description="Single BACnet device instance (0–4194303)"
    )


def _device_instance_range_json_schema(schema: dict) -> None:
    """Keep start_instance before end_instance in OpenAPI (alphabetical order would flip them)."""
    props = schema.get("properties")
    if isinstance(props, dict) and "start_instance" in props and "end_instance" in props:
        schema["properties"] = {
            "start_instance": props["start_instance"],
            "end_instance": props["end_instance"],
        }
    schema["example"] = {"start_instance": 1, "end_instance": 3456799}


class DeviceInstanceRange(BaseModel):
    """Who-Is instance range; defaults match Open-FDD POST /bacnet/whois_range (WhoIsRequestRange)."""

    model_config = ConfigDict(json_schema_extra=_device_instance_range_json_schema)

    start_instance: conint(ge=0, le=4194303) = Field(
        default=1,
        description="Start device instance (0–4194303)",
    )
    end_instance: conint(ge=0, le=4194303) = Field(
        default=3456799,
        description="End device instance (0–4194303)",
    )


class DeviceInstanceValidator(BaseModel):
    device_instance: conint(ge=0, le=4194303)

    @classmethod
    def validate_instance(cls, device_instance: int):
        try:
            return cls(device_instance=device_instance).device_instance
        except ValidationError as e:
            raise HTTPException(status_code=400, detail=e.errors())


class WritePropertyRequest(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(
        ..., description="BACnet device instance (0-4194303)"
    )
    object_identifier: str = Field(
        ..., description="Object ID in the format 'objectType,instanceNumber'"
    )
    property_identifier: str = Field(
        ..., description="BACnet property name like 'present-value'"
    )
    value: Union[float, int, str] = Field(
        ..., description="Value to write, use 'null' (as string) to release override"
    )
    priority: Optional[conint(ge=1, le=16)] = Field(
        default=None,
        description="Priority slot (1-16), required if releasing with 'null'",
    )

    @field_validator("property_identifier")
    @classmethod
    def validate_property_identifier(cls, v):
        valid = set(PropertyIdentifier._enum_map.keys())
        if v not in valid:
            raise ValueError(f"Invalid property_identifier: {v}")
        return v

    @field_validator("object_identifier")
    @classmethod
    def validate_object_identifier(cls, v):
        parse_object_identifier_parts(v)
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_instance": 987654,
                "object_identifier": "analog-output,1",
                "property_identifier": "present-value",
                "value": "null",
                "priority": 1,
            }
        }
    )


class ReadMultiplePropertiesRequest(BaseModel):
    object_identifier: str = Field(
        ..., description="BACnet object in the format 'objectType,instanceNumber'"
    )
    property_identifier: str = Field(
        ..., description="BACnet property name like 'present-value'"
    )

    @field_validator("object_identifier")
    @classmethod
    def validate_object_identifier(cls, v):
        parse_object_identifier_parts(v)
        return v

    @field_validator("property_identifier")
    @classmethod
    def validate_property_identifier(cls, v):
        if v not in PropertyIdentifier._enum_map:
            raise ValueError(f"Invalid property identifier: {v}")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "object_identifier": "analog-input,2",
                "property_identifier": "present-value",
            }
        }
    )


class ReadMultiplePropertiesRequestWrapper(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_instance": 123456,
                "requests": [
                    {
                        "object_identifier": "analog-input,2",
                        "property_identifier": "present-value",
                    },
                    {
                        "object_identifier": "binary-output,3",
                        "property_identifier": "status-flags",
                    },
                ],
            }
        }
    )

    device_instance: conint(ge=0, le=4194303) = Field(
        ..., description="BACnet device instance (0-4194303)"
    )
    requests: List[ReadMultiplePropertiesRequest]


class SingleReadRequest(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(
        ..., description="Target device instance"
    )
    object_identifier: str = Field(..., description="e.g., 'analog-output,1'")
    property_identifier: str = Field(
        default="present-value", description="e.g., 'present-value'"
    )

    @field_validator("object_identifier")
    @classmethod
    def validate_object_identifier(cls, v):
        parse_object_identifier_parts(v)
        return v

    @field_validator("property_identifier")
    @classmethod
    def validate_property_identifier(cls, v):
        if v not in PropertyIdentifier._enum_map:
            raise ValueError(f"Invalid property identifier: {v}")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_instance": 987654,
                "object_identifier": "analog-output,1",
                "property_identifier": "present-value",
            }
        }
    )


class ReadPriorityArrayRequest(BaseModel):
    device_instance: conint(ge=0, le=4194303) = Field(
        ..., description="BACnet device instance"
    )
    object_identifier: str = Field(
        ..., description="Object ID in the format 'objectType,instanceNumber'"
    )

    @field_validator("object_identifier")
    @classmethod
    def validate_object_identifier(cls, v):
        parse_object_identifier_parts(v)
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_instance": 987654,
                "object_identifier": "analog-output,1",
            }
        }
    )
