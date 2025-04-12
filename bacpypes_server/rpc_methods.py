from models import (
    WritePropertyRequest,
    ReadMultiplePropertiesRequestWrapper,
    DeviceInstanceRange,
    SingleReadRequest,
    BaseResponse,
    PointUpdate,
)
from client_utils import (
    bacnet_read,
    bacnet_write,
    bacnet_rpm,
    perform_who_is,
    get_device_address,
)
from server_utils import (
    point_map,
    CommandableAnalogValueObject,
    CommandableBinaryValueObject,
)
from errors import DeviceNotFoundError

from bacpypes3.local.analog import AnalogValueObject
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.json.util import atomic_encode
import fastapi_jsonrpc as jsonrpc
import logging


# JSON-RPC Entrypoint must be defined before using it
rpc = jsonrpc.Entrypoint("")


logger = logging.getLogger("rpc_methods")


@rpc.method()
def server_hello() -> dict:
    return {"message": "BACnet RPC API ready. Use /docs to test."}


# ──────── BACNET SERVER UTILS METHODS ────────
@rpc.method()
def server_update_points(update: PointUpdate) -> dict:
    result = {}
    for name, value in update.__root__.items():
        obj = point_map.get(name)
        if obj is None:
            continue
        try:
            if isinstance(obj, BinaryValueObject):
                desired_value = (
                    "active"
                    if value in [1, True, "true", "True", "active"]
                    else "inactive"
                )
                current_value = str(obj.presentValue).lower()
                if current_value != desired_value:
                    logger.info(
                        f"BV update: {name} changed from {current_value} → {desired_value}"
                    )
                    obj.presentValue = desired_value
                    result[name] = f"changed from {current_value} → {desired_value}"
                else:
                    logger.debug(f"BV unchanged: {name} = {current_value}")
            elif isinstance(obj, AnalogValueObject):
                new_value = float(value)
                current_value = float(obj.presentValue)
                if current_value != new_value:
                    logger.info(
                        f"AV update: {name} changed from {current_value} → {new_value}"
                    )
                    obj.presentValue = new_value
                    result[name] = f"changed from {current_value} → {new_value}"
                else:
                    logger.debug(f"AV unchanged: {name} = {current_value}")
        except Exception as e:
            logger.error(f"Error updating {name}: {e}")
            result[name] = f"error: {e}"
    return {"updated_bacnet_points": result}


@rpc.method()
def server_read_commandable() -> dict:
    result = {}
    for name, obj in point_map.items():
        if isinstance(
            obj, (CommandableAnalogValueObject, CommandableBinaryValueObject)
        ):
            try:
                value = obj.presentValue
                result[name] = (
                    float(value)
                    if isinstance(obj, CommandableAnalogValueObject)
                    else str(value)
                )
            except Exception as e:
                logger.error(f"Error reading {name}: {e}")
                result[name] = f"error: {e}"
    return result


@rpc.method()
def server_read_all_values() -> dict:
    result = {}
    for name, obj in point_map.items():
        try:
            val = obj.presentValue
            result[name] = atomic_encode(val) if hasattr(val, "encode") else str(val)
        except Exception as e:
            logger.error(f"Error reading {name}: {e}")
            result[name] = f"error: {e}"
    return result


# ──────── BACNET CLIENT UTILS METHODS ────────


@rpc.method()
async def client_read_property(request: SingleReadRequest) -> dict:
    return await bacnet_read(
        request.device_instance,
        request.object_identifier,
        request.property_identifier,
    )


@rpc.method()
async def client_write_property(request: WritePropertyRequest) -> dict:
    return await bacnet_write(
        device_instance=request.device_instance,
        object_identifier=request.object_identifier,
        property_identifier=request.property_identifier,
        value=request.value,
        priority=request.priority or -1,
    )


@rpc.method()
async def client_read_multiple(
    request: ReadMultiplePropertiesRequestWrapper,
) -> BaseResponse:
    try:
        address = await get_device_address(request.device_instance)
    except Exception as e:
        logger.error(f"Could not resolve device address: {e}")
        raise DeviceNotFoundError(
            data={"instance": request.device_instance, "detail": str(e)}
        )

    args = []
    for r in request.requests:
        args.append(r.object_identifier)
        args.append(r.property_identifier)

    try:
        result = await bacnet_rpm(address, *args)
        return BaseResponse(
            success=True,
            message="Read Multiple complete",
            data={"results": result},
        )
    except Exception as e:
        logger.error(f"RPM failed: {e}")
        # Still a generic error here — can define RPMError later if needed
        raise DeviceNotFoundError(
            data={"instance": request.device_instance, "detail": str(e)}
        )


@rpc.method()
async def client_whois_range(request: DeviceInstanceRange) -> BaseResponse:
    try:
        data = await perform_who_is(
            start_instance=request.start_instance,
            end_instance=request.end_instance,
        )
        return BaseResponse(
            success=True, message="Who-Is scan complete", data={"devices": data}
        )
    except Exception as e:
        logger.error(f"Who-Is scan failed: {e}")
        raise jsonrpc.JsonRpcError(code=500, message="Who-Is scan failed", data=str(e))


# expose this to rpc_app.py
__all__ = ["api_v1"]
