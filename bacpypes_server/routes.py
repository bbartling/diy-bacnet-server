# routes.py
import logging
from fastapi import FastAPI
from models import PointUpdate
from utils import point_map, CommandableAnalogValueObject, CommandableBinaryValueObject

from bacpypes3.local.analog import AnalogValueObject
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.json.util import (
    sequence_to_json,
    atomic_encode,
    extendedlist_to_json_list,
)


logger = logging.getLogger("routes")


def register_routes(app: FastAPI):
    @app.get("/")
    def hello():
        return {"message": "BACnet API ready. Use /docs to test."}

    @app.post("/update")
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

    @app.get("/read_commandable")
    def read_commandable_values():
        result = {}
        for name, obj in point_map.items():
            if isinstance(
                obj, (CommandableAnalogValueObject, CommandableBinaryValueObject)
            ):
                try:
                    value = obj.presentValue
                    # For commandable analog, convert to float
                    if isinstance(obj, CommandableAnalogValueObject):
                        result[name] = float(value)
                    else:
                        result[name] = str(value)
                except Exception as e:
                    logger.error(f"Error reading {name}: {e}")
                    result[name] = f"error: {e}"
        return result

    @app.get("/read_values")
    def read_all_values():
        result = {}
        for name, obj in point_map.items():
            try:
                val = obj.presentValue
                if hasattr(val, "encode"):  # Atomic
                    result[name] = atomic_encode(val)
                else:
                    result[name] = str(val)
            except Exception as e:
                logger.error(f"Error reading {name}: {e}")
                result[name] = f"error: {e}"
        return result
