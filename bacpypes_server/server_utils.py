# bacnet_loader.py
import os
import glob
import csv
import logging
from typing import Dict
from difflib import get_close_matches

from bacpypes3.local.analog import AnalogValueObject
from bacpypes3.local.binary import BinaryValueObject
from bacpypes3.local.cmd import Commandable
from bacpypes3.local.object import Object
from bacpypes3.primitivedata import Real
from bacpypes3.basetypes import EngineeringUnits


logger = logging.getLogger("loader")

point_map: Dict[str, Object] = {}


class CommandableAnalogValueObject(Commandable, AnalogValueObject):
    """Commandable Analog Value Object"""


class CommandableBinaryValueObject(Commandable, BinaryValueObject):
    """Commandable Binary Value Object"""


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
csv_files = glob.glob(os.path.join(ROOT_DIR, "*.csv"))
if len(csv_files) != 1:
    raise FileNotFoundError(
        f"Expected exactly one CSV file in {ROOT_DIR}, found: {csv_files}"
    )
CSV_FILE = csv_files[0]
logger.info(f"Detected CSV file: {CSV_FILE}")

UNIT_NAME_TO_ENUM = {
    name: getattr(EngineeringUnits, name)
    for name in dir(EngineeringUnits)
    if not name.startswith("_") and isinstance(getattr(EngineeringUnits, name), int)
}


def resolve_unit(unit_str):
    if not unit_str or unit_str.strip().lower() in {"null", "none", ""}:
        return EngineeringUnits.noUnits
    unit_str_clean = unit_str.replace(" ", "").replace("_", "").lower()
    normalized_keys = {
        name: name.replace(" ", "").replace("_", "").lower()
        for name in UNIT_NAME_TO_ENUM
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

        for idx, row in enumerate(reader, start=2):
            try:
                name = row["Name"].strip()
                point_type = row.get("PointType", "").strip().upper()
                unit_str = row.get("Units", "").strip()
                commandable = row.get("Commandable", "").strip().upper() == "Y"

                if not name or point_type not in {"AV", "BV"}:
                    logger.warning(f"Skipping invalid row {idx}: {row}")
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
                logger.debug(
                    f"Added {point_type} {av_instance_id if point_type == 'AV' else bv_instance_id}: "
                    f"{name} (commandable={commandable}) with units '{unit_str}'"
                )
            except Exception as e:
                logger.error(f"Failed to create object from row {idx}: {e}")
