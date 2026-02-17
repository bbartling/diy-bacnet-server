"""
Deep BACnet discovery into RDF (BACnetGraph) — returns TTL for BRICK/Open-FDD merge.

Uses bacpypes3.rdf.BACnetGraph and rdflib. Requires: pip install rdflib
"""

from __future__ import annotations

import io
import logging
from typing import Any

from bacpypes_server import client_utils

logger = logging.getLogger("rdf_scan")


def _get_rdflib_and_bacnet_graph():
    """Lazy import so rdflib is only required when this RPC is used."""
    try:
        from rdflib import Graph
        from bacpypes3.rdf import BACnetGraph
        return Graph, BACnetGraph
    except ImportError as e:
        raise RuntimeError(
            "RDF discovery requires rdflib. Install with: pip install rdflib"
        ) from e


async def _get_object_list_robust(device_address, device_identifier) -> list:
    """Read object-list; fallback to index-by-index if array read fails."""
    try:
        val = await client_utils.app.read_property(
            device_address, device_identifier, "object-list"
        )
        if isinstance(val, list):
            return val
    except Exception as e:
        logger.debug("Object-list array read failed: %s", e)

    try:
        from bacpypes3.apdu import AbortPDU
        from bacpypes3.apdu import ErrorRejectAbortNack

        length = await client_utils.app.read_property(
            device_address, device_identifier, "object-list", array_index=0
        )
        obj_list = []
        for i in range(length):
            obj_id = await client_utils.app.read_property(
                device_address,
                device_identifier,
                "object-list",
                array_index=i + 1,
            )
            obj_list.append(obj_id)
        return obj_list
    except Exception as e:
        logger.warning("Object-list index fallback failed: %s", e)
        return []


def _format_priority_array(pa) -> str:
    """Compact string for priority-array (for CSV/logging)."""
    if not pa:
        return ""
    try:
        from bacpypes3.constructeddata import AnyAtomic

        out = {}
        for i, p_val in enumerate(pa):
            if p_val is None:
                continue
            choice = getattr(p_val, "_choice", None)
            if choice:
                v = getattr(p_val, choice, None)
                if isinstance(v, AnyAtomic):
                    v = v.get_value()
                out[i + 1] = str(v)
        return "{" + ", ".join(f"{k}: {v}" for k, v in out.items()) + "}"
    except Exception:
        return str(pa)


def _require_app():
    """Raise a clear error if BACnet stack (app) is not initialized."""
    if client_utils.app is None:
        raise RuntimeError(
            "BACnet stack not initialized (app is None). "
            "Start the server with BACnet stack enabled (e.g. run main.py with adapter config)."
        )


async def discovery_to_rdf(
    start_instance: int,
    end_instance: int,
) -> dict[str, Any]:
    """
    Who-Is in range, then for each device read object-list and key properties,
    build RDF with BACnetGraph, serialize to Turtle.
    Can be slow for large ranges; prefer client_discovery_to_rdf_device per device.
    Returns {"ttl": str, "summary": {"devices": int, "objects": int}}.
    """
    _require_app()
    Graph, BACnetGraph = _get_rdflib_and_bacnet_graph()

    i_ams = await client_utils.app.who_is(start_instance, end_instance)
    if not i_ams:
        return {
            "ttl": _prefixes_only(Graph),
            "summary": {"devices": 0, "objects": 0},
        }

    g = Graph()
    bacnet_graph = BACnetGraph(g)
    total_objects = 0
    for i_am in i_ams:
        total_objects += await _scan_one_device_to_graph(g, bacnet_graph, i_am, Graph, BACnetGraph)

    buf = io.BytesIO()
    g.serialize(buf, format="turtle")
    ttl = buf.getvalue().decode("utf-8")

    return {
        "ttl": ttl,
        "summary": {"devices": len(i_ams), "objects": total_objects},
    }


def _prefixes_only(Graph) -> str:
    """Minimal TTL with just prefixes when no devices found."""
    g = Graph()
    buf = io.BytesIO()
    g.serialize(buf, format="turtle")
    return buf.getvalue().decode("utf-8")


async def _scan_one_device_to_graph(
    g, bacnet_graph, i_am, Graph, BACnetGraph
) -> int:
    """
    Scan one device (one I-Am) into the RDF graph. Returns number of objects added.
    Imports kept local to avoid circular/order issues.
    """
    from bacpypes3.pdu import Address
    from bacpypes3.primitivedata import ObjectIdentifier, PropertyIdentifier
    from bacpypes3.vendor import get_vendor_info
    from bacpypes3.constructeddata import AnyAtomic
    from bacpypes3.apdu import AbortPDU, ErrorRejectAbortNack

    dev_addr: Address = i_am.pduSource
    dev_id: ObjectIdentifier = i_am.iAmDeviceIdentifier
    dev_inst = dev_id[1]
    vendor_info = get_vendor_info(i_am.vendorID)
    count = 0

    logger.info("RDF scan: device %s @ %s", dev_inst, dev_addr)
    dev_graph = bacnet_graph.create_device(dev_addr, dev_id)

    # Device object optional properties (many devices don't support "description")
    try:
        dev_name = await client_utils.app.read_property(dev_addr, dev_id, "object-name")
        setattr(dev_graph, "object-name", dev_name)
    except BaseException:
        pass
    try:
        dev_desc = await client_utils.app.read_property(dev_addr, dev_id, "description")
        setattr(dev_graph, "description", dev_desc)
    except BaseException:
        pass

    obj_list = await _get_object_list_robust(dev_addr, dev_id)
    if not obj_list:
        return 0

    props = [
        "object-name",
        "description",
        "present-value",
        "units",
        "reliability",
        "out-of-service",
        "priority-array",
    ]

    for obj_id in obj_list:
        obj_proxy = dev_graph.create_object(obj_id)
        obj_class = vendor_info.get_object_class(obj_id[0])
        if not obj_class:
            continue

        for prop_name in props:
            try:
                prop_id = PropertyIdentifier(prop_name)
            except Exception:
                continue
            if not getattr(obj_class, "get_property_type", None) or not obj_class.get_property_type(prop_id):
                continue
            try:
                val = await client_utils.app.read_property(dev_addr, obj_id, prop_name)
                setattr(obj_proxy, prop_name, val)
            except (AbortPDU, ErrorRejectAbortNack, AttributeError):
                continue
            except BaseException as e:
                logger.debug("Read %s %s: %s", obj_id, prop_name, e)

        count += 1

    return count


async def discovery_to_rdf_one_device(device_instance: int) -> dict[str, Any]:
    """
    Deep scan a single device by instance: Who-Is for that instance only, then
    object-list + key properties, build RDF, return TTL + summary.
    Same idea as discover-objects-rdf.py but one device only (fast, no long scan).
    Returns {"ttl": str, "summary": {"devices": int, "objects": int}}.
    """
    _require_app()
    Graph, BACnetGraph = _get_rdflib_and_bacnet_graph()

    i_ams = await client_utils.app.who_is(device_instance, device_instance)
    if not i_ams:
        return {
            "ttl": _prefixes_only(Graph),
            "summary": {"devices": 0, "objects": 0},
        }

    g = Graph()
    bacnet_graph = BACnetGraph(g)
    total_objects = 0
    for i_am in i_ams:
        total_objects += await _scan_one_device_to_graph(g, bacnet_graph, i_am, Graph, BACnetGraph)

    buf = io.BytesIO()
    g.serialize(buf, format="turtle")
    ttl = buf.getvalue().decode("utf-8")

    return {
        "ttl": ttl,
        "summary": {"devices": len(i_ams), "objects": total_objects},
    }
