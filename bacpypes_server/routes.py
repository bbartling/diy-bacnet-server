import logging
from fastapi import FastAPI, HTTPException, Body
from models import (
    PointUpdate,
    WritePropertyRequest,
    ReadMultiplePropertiesRequestWrapper,
    DeviceInstanceValidator,
    BaseResponse,
    DeviceInstanceRange,
    SingleReadRequest,
)
from server_utils import (
    point_map,
    CommandableAnalogValueObject,
    CommandableBinaryValueObject,
)
from client_utils import (
    bacnet_read,
    bacnet_write,
    bacnet_rpm,
    perform_who_is,
    get_device_address,
)

from bacpypes3.local.analog import AnalogValueObject
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.json.util import atomic_encode
from bacpypes3.pdu import Address


logger = logging.getLogger("routes")


def register_routes(app: FastAPI):

    # ──────── SERVER ROUTES ────────

    @app.get("/")
    def hello():
        return {"message": "BACnet API ready. Use /docs to test."}

    @app.post("/server/update")
    def update_points(update: PointUpdate):
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

    @app.get("/server/read_commandable")
    def read_commandable_values():
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

    @app.get("/server/read_values")
    def read_all_values():
        result = {}
        for name, obj in point_map.items():
            try:
                val = obj.presentValue
                result[name] = (
                    atomic_encode(val) if hasattr(val, "encode") else str(val)
                )
            except Exception as e:
                logger.error(f"Error reading {name}: {e}")
                result[name] = f"error: {e}"
        return result

    # ──────── CLIENT ROUTES ────────
    @app.post("/client/read_property")
    async def read_property(request: SingleReadRequest):
        return await bacnet_read(
            request.device_instance,
            request.object_identifier,
            request.property_identifier,
        )

    @app.post("/client/write_property")
    async def write_property(request: WritePropertyRequest):
        return await bacnet_write(
            device_instance=request.device_instance,
            object_identifier=request.object_identifier,
            property_identifier=request.property_identifier,
            value=request.value,
            priority=request.priority or -1,
        )

    @app.post("/client/read_multiple")
    async def read_multiple(request: ReadMultiplePropertiesRequestWrapper):
        # Convert device_instance to BACnet Address (via helper)
        try:
            address = await get_device_address(
                request.device_instance
            )  # Must exist in your client_utils.py
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Could not resolve device address: {e}"
            )

        # Flatten the object/property list for RPM
        args = []
        for r in request.requests:
            args.append(r.object_identifier)
            args.append(r.property_identifier)

        try:
            result = await bacnet_rpm(address, *args)
            return BaseResponse(
                success=True, message="Read Multiple complete", data={"results": result}
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"RPM failed: {e}")

    @app.post("/client/whois_range")
    async def whois_range(request: DeviceInstanceRange = Body(...)):
        """
        Perform a Who-Is scan between start_instance and end_instance.
        """
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
            raise HTTPException(status_code=500, detail=str(e))
