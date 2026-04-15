from bacpypes_server.models import (
    WritePropertyRequest,
    ReadMultiplePropertiesRequestWrapper,
    DeviceInstanceRange,
    SingleReadRequest,
    BaseResponse,
    PointUpdate,
    DeviceInstanceOnly,
    ReadPriorityArrayRequest,
    SupervisorySummary,
    ServerScheduleReadRequest,
    ServerScheduleUpdateRequest,
    parse_object_identifier_parts,
)
from bacpypes_server.client_utils import (
    bacnet_read,
    bacnet_write,
    bacnet_rpm,
    RPM_CHUNK_SIZE,
    perform_who_is,
    get_device_address,
    point_discovery,
    supervisory_logic_check,
    read_point_priority_arr,
    perform_who_is_router_to_network,
    server_schedule_to_json,
    update_server_schedule,
)
from bacpypes_server.server_utils import (
    point_map,
    commandable_point_names,
    CommandableAnalogValueObject,
    CommandableBinaryValueObject,
)

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

from bacpypes_server.errors import (
    DeviceNotFoundError,
    WhoIsFailureError,
    PriorityArrayError,
    ReadPropertyError,
    WritePropertyError,
    RPMError,
    PointDiscoveryError,
    SupervisoryCheckError,
)

from bacpypes3.json.util import atomic_encode
from bacpypes3.primitivedata import ObjectIdentifier

import fastapi_jsonrpc as jsonrpc

from bacpypes_server.fastapi_jsonrpc_compat import apply_fastapi_jsonrpc_compat

apply_fastapi_jsonrpc_compat(jsonrpc)

import logging
import traceback


logger = logging.getLogger("rpc_methods")

# This becomes the prefix path, like /bacnet
rpc = jsonrpc.Entrypoint("")


def parse_object_identifier(oid_str: str) -> ObjectIdentifier:
    """Parse 'objectType,instanceNumber' into a BACnet ObjectIdentifier (reuses models validation)."""
    obj_type, obj_inst = parse_object_identifier_parts(oid_str)
    return ObjectIdentifier((obj_type, obj_inst))


@rpc.method()
def server_hello() -> dict:
    return {"message": "BACnet RPC API ready. Interactive docs are disabled; use Open-FDD BACnet tools or JSON-RPC."}


# ──────── BACNET SERVER UTILS METHODS ────────
@rpc.method()
def server_update_points(update: PointUpdate) -> dict:
    result = {}
    for name, value in update.root.items():

        if name in commandable_point_names:
            logger.warning(
                f"Skipping update to commandable point '{name}' to avoid conflict"
            )
            result[name] = (
                "skipped because point is configured as a writeable point in server object map"
            )
            continue

        obj = point_map.get(name)
        if obj is None:
            logger.warning(f"Point '{name}' not found in server object map")
            result[name] = "not found"
            continue
        try:
            if isinstance(obj, (AnalogInputObject, AnalogValueObject, AnalogOutputObject)):
                new_value = float(value)
                current_value = float(obj.presentValue)
                if current_value != new_value:
                    logger.info(
                        f"Analog update: {name} changed from {current_value} → {new_value}"
                    )
                    obj.presentValue = new_value
                    result[name] = f"changed from {current_value} → {new_value}"
                else:
                    logger.debug(f"Analog unchanged: {name} = {current_value}")
            elif isinstance(obj, (BinaryInputObject, BinaryValueObject, BinaryOutputObject)):
                desired_value = (
                    "active"
                    if value in [1, True, "true", "True", "active"]
                    else "inactive"
                )
                current_value = str(obj.presentValue).lower()
                if current_value != desired_value:
                    logger.info(
                        f"Binary update: {name} changed from {current_value} → {desired_value}"
                    )
                    obj.presentValue = desired_value
                    result[name] = f"changed from {current_value} → {desired_value}"
                else:
                    logger.debug(f"Binary unchanged: {name} = {current_value}")
            elif isinstance(obj, (MultiStateInputObject, MultiStateValueObject, MultiStateOutputObject)):
                new_value = int(value)
                current_value = int(obj.presentValue)
                if current_value != new_value:
                    logger.info(
                        f"Multistate update: {name} changed from {current_value} → {new_value}"
                    )
                    obj.presentValue = new_value
                    result[name] = f"changed from {current_value} → {new_value}"
                else:
                    logger.debug(f"Multistate unchanged: {name} = {current_value}")
            else:
                result[name] = "unsupported object type for update"
        except Exception as e:
            logger.error(f"Error updating {name}: {e}")
            result[name] = f"error: {e}"
    return {"updated_bacnet_points": result}


@rpc.method()
def server_read_commandable() -> dict:
    result = {}
    commandable_types = (
        CommandableAnalogValueObject,
        CommandableBinaryValueObject,
        AnalogOutputObject,
        BinaryOutputObject,
        MultiStateOutputObject,
    )
    for name, obj in point_map.items():
        if isinstance(obj, commandable_types) or (
            isinstance(obj, MultiStateValueObject) and name in commandable_point_names
        ):
            try:
                value = obj.presentValue
                if isinstance(obj, (CommandableAnalogValueObject, AnalogOutputObject)):
                    result[name] = float(value)
                elif isinstance(obj, (CommandableBinaryValueObject, BinaryOutputObject)):
                    result[name] = str(value)
                else:
                    result[name] = int(value)
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


@rpc.method()
def server_read_schedule(request: ServerScheduleReadRequest) -> dict:
    obj = point_map.get(request.name)
    if obj is None:
        return {"name": request.name, "status": "not found"}
    if not isinstance(obj, ScheduleObject):
        return {
            "name": request.name,
            "status": "error",
            "detail": "point exists but is not a Schedule object",
        }
    return {"name": request.name, "status": "ok", "schedule": server_schedule_to_json(obj)}


@rpc.method()
def server_update_schedule(update: ServerScheduleUpdateRequest) -> dict:
    obj = point_map.get(update.name)
    if obj is None:
        return {"name": update.name, "status": "not found"}
    if not isinstance(obj, ScheduleObject):
        return {
            "name": update.name,
            "status": "error",
            "detail": "point exists but is not a Schedule object",
        }

    changed = update_server_schedule(
        obj=obj,
        schedule_default=update.schedule_default,
        weekly_schedule=update.weekly_schedule,
    )
    return {
        "name": update.name,
        "status": "updated",
        "changed": changed,
        "schedule": server_schedule_to_json(obj),
    }


# ──────── BACNET CLIENT UTILS METHODS ────────


@rpc.method()
async def client_read_property(request: SingleReadRequest) -> dict:
    try:
        return await bacnet_read(
            request.device_instance,
            request.object_identifier,
            request.property_identifier,
        )
    except Exception as e:
        logger.error(f"Read property failed: {e}")
        raise ReadPropertyError(
            data={"object_identifier": request.object_identifier, "detail": str(e)}
        )


@rpc.method()
async def client_write_property(request: WritePropertyRequest) -> dict:
    try:
        return await bacnet_write(
            device_instance=request.device_instance,
            object_identifier=request.object_identifier,
            property_identifier=request.property_identifier,
            value=request.value,
            priority=request.priority,
        )
    except Exception as e:
        logger.error(f"Write property failed: {e}")
        raise WritePropertyError(
            data={"object_identifier": request.object_identifier, "detail": str(e)}
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

    # Chunk requests to stay under APDU/MTU limits (avoids crashes on large reads)
    combined: list = []
    for i in range(0, len(request.requests), RPM_CHUNK_SIZE):
        chunk = request.requests[i : i + RPM_CHUNK_SIZE]
        args = []
        for r in chunk:
            args.append(r.object_identifier)
            args.append(r.property_identifier)
        try:
            result = await bacnet_rpm(address, *args)
            combined.extend(result)
        except Exception as e:
            logger.error(f"RPM chunk failed: {e}")
            raise RPMError(data={"instance": request.device_instance, "detail": str(e)})

    return BaseResponse(
        success=True,
        message="Read Multiple complete",
        data={"results": combined},
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
        raise WhoIsFailureError(
            data={
                "detail": str(e),
                "start_instance": request.start_instance,
                "end_instance": request.end_instance,
            }
        )


@rpc.method()
async def client_point_discovery(instance: DeviceInstanceOnly) -> BaseResponse:
    try:
        data = await point_discovery(instance.device_instance)
        return BaseResponse(
            success=True,
            message="Point discovery successful",
            data=data,
        )
    except PointDiscoveryError:
        raise  # Re-raise it cleanly without nesting
    except Exception as e:
        raise PointDiscoveryError(
            data={
                "instance": instance.device_instance,
                "detail": f"Unexpected error during point discovery: {e}",
            }
        )


@rpc.method()
async def client_supervisory_logic_checks(
    instance: DeviceInstanceOnly,
) -> SupervisorySummary:
    try:
        return await supervisory_logic_check(instance.device_instance)
    except Exception as e:
        raise SupervisoryCheckError(
            data={"instance": instance.device_instance, "detail": str(e)}
        )


@rpc.method()
async def client_read_point_priority_array(request: ReadPriorityArrayRequest) -> list:
    logger.info(
        f"Reading priority array for device_instance={request.device_instance}, object_identifier={request.object_identifier}"
    )
    try:
        address = await get_device_address(request.device_instance)
        object_id = parse_object_identifier(request.object_identifier)
        priority_array = await read_point_priority_arr(address, object_id)

        if priority_array is None:
            raise PriorityArrayError(
                data={"detail": "No priority array found or empty response"}
            )

        return priority_array

    except PriorityArrayError:
        raise
    except Exception as e:
        logger.error(
            f"Unexpected error reading priority-array {request.object_identifier}: {e}"
        )
        raise PriorityArrayError(data={"detail": str(e)})


@rpc.method()
async def client_whois_router_to_network() -> BaseResponse:
    try:
        results = await perform_who_is_router_to_network()
        return BaseResponse(
            success=True,
            message="Who-Is-Router-To-Network scan complete",
            data={"routers": results},
        )
    except Exception as e:
        logger.error(f"Who-Is-Router-To-Network failed: {e}")
        raise WhoIsFailureError(data={"detail": str(e)})
