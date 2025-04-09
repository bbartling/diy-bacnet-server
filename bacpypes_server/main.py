import asyncio
import os
import glob
import csv
from difflib import get_close_matches
from typing import Dict

from fastapi import FastAPI
from pydantic import RootModel
import uvicorn

from bacpypes3.debugging import bacpypes_debugging, ModuleLogger
from bacpypes3.argparse import SimpleArgumentParser
from bacpypes3.ipv4.app import Application
from bacpypes3.local.analog import AnalogValueObject
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.local.device import DeviceObject
from bacpypes3.local.object import Object
from bacpypes3.local.cmd import Commandable
from bacpypes3.primitivedata import Real
from bacpypes3.basetypes import EngineeringUnits

# Debug setup
_debug = 1
_log = ModuleLogger(globals())


@bacpypes_debugging
class CommandableAnalogValueObject(Commandable, AnalogValueObject):
    """Commandable Analog Value Object"""


@bacpypes_debugging
class CommandableBinaryValueObject(Commandable, BinaryValueObject):
    """Commandable Binary Value Object"""


# FastAPI app
api_app = FastAPI(
    title="BACnet REST API",
    description="Update and Read BACnet points from Node-RED",
    version="1.0",
)

# Global point map
point_map: Dict[str, Object] = {}

# CSV file detection
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
csv_files = glob.glob(os.path.join(ROOT_DIR, "*.csv"))
if len(csv_files) != 1:
    raise FileNotFoundError(
        f"Expected exactly one CSV file in {ROOT_DIR}, found: {csv_files}"
    )
CSV_FILE = csv_files[0]
_log.info(f"Detected CSV file: {CSV_FILE}")

# Engineering units mapping
UNIT_NAME_TO_ENUM = {
    name: getattr(EngineeringUnits, name)
    for name in dir(EngineeringUnits)
    if not name.startswith("_") and isinstance(getattr(EngineeringUnits, name), int)
}


# Pydantic wrapper
class PointUpdate(RootModel[Dict[str, float | bool]]):
    pass


def resolve_unit(unit_str):
    if not unit_str or unit_str.strip().lower() in {"null", "none", ""}:
        return EngineeringUnits.noUnits

    unit_str_clean = unit_str.replace(" ", "").replace("_", "").lower()
    normalized_keys = {
        name: name.replace(" ", "").replace("_", "").lower()
        for name in UNIT_NAME_TO_ENUM.keys()
    }

    matches = get_close_matches(
        unit_str_clean, normalized_keys.values(), n=1, cutoff=0.6
    )
    if matches:
        best_match_key = [k for k, v in normalized_keys.items() if v == matches[0]][0]
        return UNIT_NAME_TO_ENUM[best_match_key]

    return EngineeringUnits.noUnits


async def load_csv_and_create_objects(app):
    required_headers = {"Name", "PointType", "Units", "Commandable"}
    with open(CSV_FILE, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        headers = set(reader.fieldnames or [])
        missing_headers = required_headers - headers
        if missing_headers:
            raise ValueError(f"CSV missing required columns: {missing_headers}")

        av_instance_id = 1
        bv_instance_id = 1

        for idx, row in enumerate(reader, start=2):  # start=2 for CSV line numbers
            try:
                name = row["Name"].strip()
                point_type = row.get("PointType", "").strip().upper()
                unit_str = row.get("Units", "").strip()
                commandable = row.get("Commandable", "").strip().upper() == "Y"

                if not name or point_type not in {"AV", "BV"}:
                    _log.warning(f"Skipping invalid row {idx}: {row}")
                    continue

                engineering_unit = resolve_unit(unit_str)

                if point_type == "AV":
                    obj = (
                        CommandableAnalogValueObject
                        if commandable
                        else AnalogValueObject
                    )(
                        objectIdentifier=("analogValue", av_instance_id),
                        objectName=name,
                        presentValue=Real(0.0),
                        statusFlags=[0, 0, 0, 0],
                        covIncrement=1.0,
                        units=engineering_unit,
                        description=f"REST-Updatable Analog Value from CSV",
                    )
                    av_instance_id += 1

                elif point_type == "BV":
                    obj = (
                        CommandableBinaryValueObject
                        if commandable
                        else BinaryValueObject
                    )(
                        objectIdentifier=("binaryValue", bv_instance_id),
                        objectName=name,
                        presentValue="inactive",
                        statusFlags=[0, 0, 0, 0],
                        description=f"REST-Updatable Binary Value from CSV",
                    )
                    bv_instance_id += 1

                app.add_object(obj)
                point_map[name] = obj
                _log.debug(
                    f"Added {point_type} {av_instance_id if point_type == 'AV' else bv_instance_id}: "
                    f"{name} (commandable={commandable}) with units '{unit_str}'"
                )

            except Exception as e:
                _log.error(f"Failed to create object from row {idx}: {e}")


@api_app.get("/")
def hello():
    return {"message": "BACnet API ready. Use /docs to test."}


@api_app.post("/update")
def update_points(update: PointUpdate):
    result = {}
    for name, value in update.root.items():
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
                    _log.info(
                        f"BV update: {name} changed from {current_value} → {desired_value}"
                    )
                    obj.presentValue = desired_value
                    result[name] = f"changed from {current_value} → {desired_value}"
                else:
                    _log.debug(f"BV unchanged: {name} = {current_value}")

            elif isinstance(obj, AnalogValueObject):
                new_value = float(value)
                current_value = float(obj.presentValue)
                if current_value != new_value:
                    _log.info(
                        f"AV update: {name} changed from {current_value} → {new_value}"
                    )
                    obj.presentValue = new_value
                    result[name] = f"changed from {current_value} → {new_value}"
                else:
                    _log.debug(f"AV unchanged: {name} = {current_value}")
        except Exception as e:
            _log.error(f"Error updating {name}: {e}")
            result[name] = f"error: {e}"

    return {"updated_bacnet_points": result}


@api_app.get("/read")
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
                _log.error(f"Error reading {name}: {e}")
                result[name] = f"error: {e}"
    return result


async def start_api_server():
    config = uvicorn.Config(api_app, host="127.0.0.1", port=8080, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    args = SimpleArgumentParser().parse_args()
    try:
        bacnet_app = Application.from_args(args)
        await load_csv_and_create_objects(bacnet_app)
    except Exception as e:
        _log.error(f"Startup error: {e}")
        return  # Prevent FastAPI from launching if load fails

    asyncio.create_task(start_api_server())
    _log.info("FastAPI REST API started at http://localhost:8080/docs")
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting.")
