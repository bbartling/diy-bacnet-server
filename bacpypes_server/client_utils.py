from typing import List, Union

from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier, Null
from bacpypes3.apdu import (
    ErrorRejectAbortNack,
    PropertyReference,
    PropertyIdentifier,
    ErrorType,
)
from bacpypes3.constructeddata import AnyAtomic, Sequence, Array, List
from bacpypes3.vendor import get_vendor_info
from bacpypes3.primitivedata import Atomic
from bacpypes3.json.util import (
    atomic_encode,
    sequence_to_json,
    extendedlist_to_json_list,
)
from bacpypes3.primitivedata import Null
from bacpypes3.pdu import Address
from bacpypes3.primitivedata import ObjectIdentifier

from fastapi import HTTPException
import logging


logger = logging.getLogger("client_utils")


app = None  # will be set from main.py


def set_app(application):
    global app
    app = application


def _convert_to_address(address: str) -> Address:
    """
    Convert a string to a BACnet Address object.
    """
    return Address(address)


def _convert_to_object_identifier(obj_id: str) -> ObjectIdentifier:
    """
    Convert a string to a BACnet ObjectIdentifier.
    """
    object_type, instance_number = obj_id.split(",")
    return ObjectIdentifier((object_type.strip(), int(instance_number.strip())))


def parse_property_identifier(property_identifier):
    # Example parsing logic (modify as needed for your use case)
    if "," in property_identifier:
        prop_id, prop_index = property_identifier.split(",")
        return prop_id.strip(), int(prop_index.strip())
    return property_identifier, None


async def get_device_address(device_instance: int) -> Address:
    device_info = app.device_info_cache.instance_cache.get(device_instance, None)
    if device_info:
        return device_info.device_address

    i_ams = await app.who_is(device_instance, device_instance)
    if not i_ams:
        raise HTTPException(
            status_code=404, detail=f"Device {device_instance} not found"
        )
    if len(i_ams) > 1:
        raise HTTPException(
            status_code=400, detail=f"Multiple devices found: {device_instance}"
        )

    return i_ams[0].pduSource


async def bacnet_read(
    device_instance: int, object_identifier: str, property_identifier: str
):
    try:
        address = await get_device_address(device_instance)
        obj_id = ObjectIdentifier(object_identifier)

        value = await app.read_property(address, obj_id, property_identifier)

        if isinstance(value, AnyAtomic):
            value = value.get_value()

        if isinstance(value, Atomic):
            encoded = atomic_encode(value)
        elif isinstance(value, Sequence):
            encoded = sequence_to_json(value)
        elif isinstance(value, (Array, List)):
            encoded = extendedlist_to_json_list(value)
        else:
            raise HTTPException(
                status_code=400, detail=f"Unhandled type: {type(value)}"
            )

        return {property_identifier: encoded}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Read failed: {e}")


async def bacnet_write(
    device_instance: int,
    object_identifier: str,
    property_identifier: str,
    value: Union[float, int, str],
    priority: int = -1,
):
    try:
        address = await get_device_address(device_instance)
        obj_id = ObjectIdentifier(object_identifier)
        prop_id, prop_idx = parse_property_identifier(property_identifier)

        if value == "null":
            if priority is None:
                raise HTTPException(
                    status_code=400,
                    detail="Null requires a priority to release override",
                )
            value = Null(())

        result = await app.write_property(
            address, obj_id, prop_id, value, prop_idx, priority
        )
        return {"status": "success", "response": str(result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Write failed: {e}")


async def bacnet_rpm(
    address: Address,
    *args: str,
):

    logger.info(f"Received arguments for RPM: {args}")
    args_list: List[str] = list(args)

    # Convert address string to BACnet Address object
    address_obj = _convert_to_address(address)

    # Get device info from cache
    device_info = await app.device_info_cache.get_device_info(address_obj)

    # Look up vendor information
    vendor_info = get_vendor_info(device_info.vendor_identifier if device_info else 0)

    parameter_list = []
    while args_list:
        # Translate the object identifier using vendor information
        obj_id_str = args_list.pop(0)
        object_identifier = vendor_info.object_identifier(obj_id_str)
        object_class = vendor_info.get_object_class(object_identifier[0])

        if not object_class:
            logger.error(f"Unrecognized object type: {object_identifier}")
            return [{"error": f"Unrecognized object type: {object_identifier}"}]

        # Save this object identifier as a parameter
        parameter_list.append(object_identifier)

        property_reference_list = []
        while args_list:
            # Parse the property reference using vendor info
            property_reference = PropertyReference(
                propertyIdentifier=args_list.pop(0),
                vendor_info=vendor_info,
            )
            logger.info(f"Property reference: {property_reference}")

            # Check if the property is known
            if property_reference.propertyIdentifier not in (
                PropertyIdentifier.all,
                PropertyIdentifier.required,
                PropertyIdentifier.optional,
            ):
                property_type = object_class.get_property_type(
                    property_reference.propertyIdentifier
                )
                logger.info(f"Property type: {property_type}")

                if not property_type:
                    logger.error(
                        f"Unrecognized property: {property_reference.propertyIdentifier}"
                    )
                    return [
                        {
                            "error": f"Unrecognized property: {property_reference.propertyIdentifier}"
                        }
                    ]

            # Save this property reference as a parameter
            property_reference_list.append(property_reference)

            # Break if the next thing is an object identifier
            if args_list and (":" in args_list[0] or "," in args_list[0]):
                break

        # Save the property reference list as a parameter
        parameter_list.append(property_reference_list)

    if not parameter_list:
        logger.error("Object identifier expected.")
        return [{"error": "Object identifier expected."}]

    try:
        # Perform the read property multiple operation
        response = await app.read_property_multiple(address_obj, parameter_list)
    except ErrorRejectAbortNack as err:
        logger.error(f"during RPM: {err}")
        return [{"error": f"Error during RPM: {err}"}]

    # Prepare the response with either property values or error messages
    result_list = []
    for (
        object_identifier,
        property_identifier,
        property_array_index,
        property_value,
    ) in response:
        result = {
            "object_identifier": object_identifier,
            "property_identifier": property_identifier,
            "property_array_index": property_array_index,
        }
        if isinstance(property_value, ErrorType):
            result["value"] = (
                f"Error: {property_value.errorClass}, {property_value.errorCode}"
            )
        else:
            result["value"] = property_value

        result_list.append(result)

    logger.info(f"result_list: {result_list}")

    return result_list


async def perform_who_is(start_instance: int, end_instance: int):

    i_ams = await app.who_is(start_instance, end_instance)
    if not i_ams:
        no_response_str = f"No response(s) on WhoIs start_instance {start_instance} end_instance {end_instance}"
        logger.error(no_response_str)
        return no_response_str

    result = []
    for i_am in i_ams:
        logger.info("i_am: %r", i_am)

        device_address: Address = i_am.pduSource
        device_identifier: ObjectIdentifier = i_am.iAmDeviceIdentifier

        logger.info(f"{device_identifier} @ {device_address}")

        try:
            device_description: str = await app.read_property(
                device_address, device_identifier, "description"
            )
            logger.info(f"description: {device_description}")
        except ErrorRejectAbortNack as err:
            # some devices don't support the "description" property
            device_description = f"Error: {err}"
            logger.info(f"ERROR - {device_identifier} description error: {err}")

        result.append(
            {
                "i-am-device-identifier": f"{device_identifier}",
                "device-address": f"{device_address}",
                "device-description": device_description,
                "max-apdu-length-accepted": i_am.maxAPDULengthAccepted,
                "segmentation-supported": str(i_am.segmentationSupported),
                "vendor-id": i_am.vendorID,
            }
        )

    return result
