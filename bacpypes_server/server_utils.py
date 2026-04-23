# server_utils.py — CSV loading and BACnet object creation
# Supports: AI, AO, AV, BI, BO, BV, MSI, MSO, MSV, Schedule (bacpypes3.local from JoelBender/BACpypes3)
# Note: bacpypes3/local/schedule.py interpret_schedule() — if it uses call_at(absolute_timestamp),
# that is a known bug (call_at expects monotonic time). Fix: use call_later(delay_seconds, ...)
# where delay = next_transition_unix - time.time().
import os
import glob
import csv
import math
import logging
from datetime import datetime
from typing import Dict
from difflib import get_close_matches

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
from bacpypes3.local.cmd import Commandable
from bacpypes3.local.multistate import (
    MultiStateInputObject,
    MultiStateOutputObject,
    MultiStateValueObject,
)
from bacpypes3.local.object import Object
from bacpypes3.local.schedule import ScheduleObject
from bacpypes3.primitivedata import Real, Integer, Date, Time
from bacpypes3.basetypes import (
    EngineeringUnits,
    DateRange,
    DailySchedule,
    TimeValue,
    Reliability,
)


logger = logging.getLogger("loader")

# used to prevent writeable points from getting updated internally (AO, BO, MSO, and Commandable Y for AV, BV, MSV)
commandable_point_names: set[str] = set()

point_map: Dict[str, Object] = {}

# All supported CSV PointType codes (BACnet object types), normalized uppercase.
SUPPORTED_POINT_TYPES = {
    "AI",
    "AO",
    "AV",
    "BI",
    "BO",
    "BV",
    "MSI",
    "MSO",
    "MSV",
    "SCHEDULE",
}

POINTTYPE_TO_OBJECT_KIND = {
    "AI": "analogInput",
    "AO": "analogOutput",
    "AV": "analogValue",
    "BI": "binaryInput",
    "BO": "binaryOutput",
    "BV": "binaryValue",
    "MSI": "multiStateInput",
    "MSO": "multiStateOutput",
    "MSV": "multiStateValue",
    "SCHEDULE": "schedule",
}


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
    # Added "Default" to the allowed headers logic (optional check)
    required_headers = {"Name", "PointType", "Units", "Commandable"}
    
    with open(CSV_FILE, newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        headers = set(reader.fieldnames or [])
        missing_headers = required_headers - headers
        if missing_headers:
            raise ValueError(f"CSV missing required columns: {missing_headers}")

        instance_ids = {
            "analogInput": 1,
            "analogOutput": 1,
            "analogValue": 1,
            "binaryInput": 1,
            "binaryOutput": 1,
            "binaryValue": 1,
            "multiStateInput": 1,
            "multiStateOutput": 1,
            "multiStateValue": 1,
            "schedule": 1,
        }
        used_instances: set[tuple[str, int]] = set()

        for idx, row in enumerate(reader, start=2):
            try:
                name = row["Name"].strip()
                point_type = row.get("PointType", "").strip().upper()
                unit_str = row.get("Units", "").strip()
                commandable = row.get("Commandable", "").strip().upper() == "Y"
                default_val_str = row.get("Default", "").strip()
                states_str = (row.get("States") or "").strip()  # optional for MSI, MSO, MSV
                instance_str = (row.get("Instance") or "").strip()
                cov_increment_str = (row.get("CovIncrement") or "").strip()

                if not name or point_type not in SUPPORTED_POINT_TYPES:
                    logger.warning(f"Skipping invalid row {idx}: {row}")
                    continue

                obj_kind = POINTTYPE_TO_OBJECT_KIND[point_type]
                if instance_str:
                    try:
                        instance_num = int(instance_str)
                    except ValueError as err:
                        raise ValueError(
                            f"row {idx} ({name}): Instance must be an integer, got {instance_str!r}"
                        ) from err
                    if not 0 <= instance_num <= 4194303:
                        raise ValueError(
                            f"row {idx} ({name}): Instance out of BACnet range 0..4194303, got {instance_num}"
                        )
                else:
                    while (
                        instance_ids[obj_kind] <= 4194303
                        and (obj_kind, instance_ids[obj_kind]) in used_instances
                    ):
                        instance_ids[obj_kind] += 1
                    if instance_ids[obj_kind] > 4194303:
                        raise ValueError(
                            f"row {idx} ({name}): no available auto-assigned instances left for {obj_kind}"
                        )
                    instance_num = instance_ids[obj_kind]
                    instance_ids[obj_kind] += 1

                key = (obj_kind, instance_num)
                if key in used_instances:
                    raise ValueError(
                        f"row {idx} ({name}): duplicate objectIdentifier ({obj_kind}, {instance_num})"
                    )

                cov_increment = 1.0
                analog_types = {"AI", "AO", "AV"}
                if cov_increment_str:
                    if point_type in analog_types:
                        try:
                            cov_increment = float(cov_increment_str)
                        except ValueError as err:
                            raise ValueError(
                                f"row {idx} ({name}): CovIncrement must be numeric, got {cov_increment_str!r}"
                            ) from err
                        if not math.isfinite(cov_increment) or cov_increment <= 0:
                            raise ValueError(
                                f"row {idx} ({name}): CovIncrement must be a finite number > 0, got {cov_increment}"
                            )
                    else:
                        logger.warning(
                            "row %s (%s): CovIncrement is ignored for PointType=%s",
                            idx,
                            name,
                            point_type,
                        )

                engineering_unit = resolve_unit(unit_str)
                obj = None

                if point_type == "AI":
                    try:
                        initial_value = float(default_val_str) if default_val_str else 0.0
                    except ValueError:
                        initial_value = 0.0
                    obj = AnalogInputObject(
                        objectIdentifier=("analogInput", instance_num),
                        objectName=name,
                        presentValue=Real(initial_value),
                        statusFlags=[0, 0, 0, 0],
                        eventState="normal",
                        outOfService=False,
                        units=engineering_unit,
                        covIncrement=cov_increment,
                        description="Analog Input from CSV",
                    )

                elif point_type == "AO":
                    try:
                        initial_value = float(default_val_str) if default_val_str else 0.0
                    except ValueError:
                        initial_value = 0.0
                    obj = AnalogOutputObject(
                        objectIdentifier=("analogOutput", instance_num),
                        objectName=name,
                        presentValue=Real(initial_value),
                        statusFlags=[0, 0, 0, 0],
                        eventState="normal",
                        outOfService=False,
                        units=engineering_unit,
                        covIncrement=cov_increment,
                        relinquishDefault=Real(initial_value),
                        description="Analog Output from CSV",
                    )
                    commandable_point_names.add(name)

                elif point_type == "AV":
                    try:
                        initial_value = float(default_val_str) if default_val_str else 0.0
                    except ValueError:
                        initial_value = 0.0
                    obj = (
                        CommandableAnalogValueObject
                        if commandable
                        else AnalogValueObject
                    )(
                        objectIdentifier=("analogValue", instance_num),
                        objectName=name,
                        presentValue=Real(initial_value),
                        relinquishDefault=Real(initial_value) if commandable else None,
                        statusFlags=[0, 0, 0, 0],
                        covIncrement=cov_increment,
                        units=engineering_unit,
                        description="Analog Value from CSV",
                    )
                    if commandable:
                        commandable_point_names.add(name)

                elif point_type == "BI":
                    is_active = default_val_str.lower() in {"true", "active", "1", "y", "yes", "on"} if default_val_str else False
                    initial_value = "active" if is_active else "inactive"
                    obj = BinaryInputObject(
                        objectIdentifier=("binaryInput", instance_num),
                        objectName=name,
                        presentValue=initial_value,
                        statusFlags=[0, 0, 0, 0],
                        eventState="normal",
                        outOfService=False,
                        polarity="normal",
                        description="Binary Input from CSV",
                    )

                elif point_type == "BO":
                    is_active = default_val_str.lower() in {"true", "active", "1", "y", "yes", "on"} if default_val_str else False
                    initial_value = "active" if is_active else "inactive"
                    obj = BinaryOutputObject(
                        objectIdentifier=("binaryOutput", instance_num),
                        objectName=name,
                        presentValue=initial_value,
                        statusFlags=[0, 0, 0, 0],
                        eventState="normal",
                        outOfService=False,
                        polarity="normal",
                        relinquishDefault=initial_value,
                        description="Binary Output from CSV",
                    )
                    commandable_point_names.add(name)

                elif point_type == "BV":
                    is_active = default_val_str.lower() in {"true", "active", "1", "y", "yes", "on"} if default_val_str else False
                    initial_value = "active" if is_active else "inactive"
                    obj = (
                        CommandableBinaryValueObject
                        if commandable
                        else BinaryValueObject
                    )(
                        objectIdentifier=("binaryValue", instance_num),
                        objectName=name,
                        presentValue=initial_value,
                        relinquishDefault=initial_value if commandable else None,
                        statusFlags=[0, 0, 0, 0],
                        description="Binary Value from CSV",
                    )
                    if commandable:
                        commandable_point_names.add(name)

                elif point_type == "MSI":
                    try:
                        initial_value = int(default_val_str) if default_val_str else 1
                    except ValueError:
                        initial_value = 1
                    num_states = 2
                    if states_str:
                        try:
                            num_states = max(2, int(states_str))
                        except ValueError:
                            pass
                    obj = MultiStateInputObject(
                        objectIdentifier=("multiStateInput", instance_num),
                        objectName=name,
                        presentValue=initial_value,
                        statusFlags=[0, 0, 0, 0],
                        eventState="normal",
                        outOfService=False,
                        numberOfStates=num_states,
                        description="Multistate Input from CSV",
                    )

                elif point_type == "MSO":
                    try:
                        initial_value = int(default_val_str) if default_val_str else 1
                    except ValueError:
                        initial_value = 1
                    num_states = 2
                    if states_str:
                        try:
                            num_states = max(2, int(states_str))
                        except ValueError:
                            pass
                    obj = MultiStateOutputObject(
                        objectIdentifier=("multiStateOutput", instance_num),
                        objectName=name,
                        presentValue=initial_value,
                        statusFlags=[0, 0, 0, 0],
                        eventState="normal",
                        outOfService=False,
                        numberOfStates=num_states,
                        relinquishDefault=initial_value,
                        description="Multistate Output from CSV",
                    )
                    commandable_point_names.add(name)

                elif point_type == "MSV":
                    try:
                        initial_value = int(default_val_str) if default_val_str else 1
                    except ValueError:
                        initial_value = 1
                    num_states = 2
                    if states_str:
                        try:
                            num_states = max(2, int(states_str))
                        except ValueError:
                            pass
                    obj = MultiStateValueObject(
                        objectIdentifier=("multiStateValue", instance_num),
                        objectName=name,
                        presentValue=initial_value,
                        statusFlags=[0, 0, 0, 0],
                        eventState="normal",
                        outOfService=False,
                        numberOfStates=num_states,
                        description="Multistate Value from CSV",
                    )
                    if commandable:
                        commandable_point_names.add(name)

                elif point_type == "SCHEDULE":
                    # Keep this minimal for broad BACpypes3 compatibility.
                    # Extra optional fields can fail on some versions and cause
                    # the row to be skipped silently in objectList discovery.
                    def _bacnet_date(y: int, m: int, d: int) -> Date:
                        dt = datetime(y, m, d)
                        dow = dt.weekday() + 1  # BACnet 1=Monday
                        return Date((y - 1900, m, d, dow))

                    def _time_val(h: int, m: int, s: int, val: int) -> TimeValue:
                        return TimeValue(time=Time((h, m, s, 0)), value=Integer(val))

                    weekday = DailySchedule(
                        daySchedule=[
                            _time_val(8, 0, 0, 1),
                            _time_val(17, 0, 0, 0),
                        ]
                    )
                    weekend = DailySchedule(daySchedule=[_time_val(0, 0, 0, 0)])
                    weekly = [weekday, weekday, weekday, weekday, weekday, weekend, weekend]
                    schedule_kwargs = dict(
                        objectIdentifier=("schedule", instance_num),
                        objectName=name,
                        presentValue=Integer(0),
                        effectivePeriod=DateRange(
                            startDate=_bacnet_date(2024, 1, 1),
                            endDate=_bacnet_date(2030, 12, 31),
                        ),
                        weeklySchedule=weekly,
                        scheduleDefault=Integer(0),
                        description="Schedule from CSV (M-F 8-17)",
                    )
                    # Expose exception-schedule when the BACpypes3 build supports it.
                    # Fall back gracefully for older/incompatible versions.
                    try:
                        obj = ScheduleObject(
                            **schedule_kwargs,
                            exceptionSchedule=[],
                        )
                        logger.debug(
                            "Schedule %s created with empty exceptionSchedule support",
                            name,
                        )
                    except TypeError as exc:
                        # Only fall back when this BACpypes3 build does not accept
                        # the exceptionSchedule keyword; re-raise unrelated constructor
                        # errors so real bugs are not hidden.
                        msg = str(exc)
                        if "exceptionSchedule" in msg and (
                            "unexpected keyword" in msg or "required positional argument" in msg
                        ):
                            obj = ScheduleObject(**schedule_kwargs)
                            logger.warning(
                                "Schedule %s created without exceptionSchedule property support",
                                name,
                            )
                        else:
                            raise

                if obj is not None:
                    used_instances.add(key)
                    app.add_object(obj)
                    point_map[name] = obj
                    logger.debug(f"Added {point_type} {name} (Cmd={commandable})")

            except Exception as e:
                logger.error(f"Failed to create object from row {idx}: {e}", exc_info=True)
