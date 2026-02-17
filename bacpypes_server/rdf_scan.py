"""
Deep BACnet discovery into RDF (BACnetGraph) — returns TTL for BRICK/Open-FDD merge.

Uses bacpypes3.rdf.BACnetGraph and rdflib. Requires: pip install rdflib
"""

from __future__ import annotations

import io
import logging
from typing import Any

from bacpypes_server.client_utils import app

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
        val = await app.read_property(
            device_address, device_identifier, "object-list"
        )
        if isinstance(val, list):
            return val
    except Exception as e:
        logger.debug("Object-list array read failed: %s", e)

    try:
        from bacpypes3.apdu import AbortPDU
        from bacpypes3.apdu import ErrorRejectAbortNack

        length = await app.read_property(
            device_address, device_identifier, "object-list", array_index=0
        )
        obj_list = []
        for i in range(length):
            obj_id = await app.read_property(
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


async def discovery_to_rdf(
    start_instance: int,
    end_instance: int,
) -> dict[str, Any]:
    """
    Who-Is in range, then for each device read object-list and key properties,
    build RDF with BACnetGraph, serialize to Turtle.
    Returns {"ttl": str, "summary": {"devices": int, "objects": int}}.
    """
    Graph, BACnetGraph = _get_rdflib_and_bacnet_graph()

    from bacpypes3.pdu import Address
    from bacpypes3.primitivedata import ObjectIdentifier, PropertyIdentifier
    from bacpypes3.vendor import get_vendor_info
    from bacpypes3.constructeddata import AnyAtomic
    from bacpypes3.apdu import AbortPDU, ErrorRejectAbortNack

    i_ams = await app.who_is(start_instance, end_instance)
    if not i_ams:
        return {
            "ttl": _prefixes_only(Graph),
            "summary": {"devices": 0, "objects": 0},
        }

    g = Graph()
    bacnet_graph = BACnetGraph(g)
    total_objects = 0

    for i_am in i_ams:
        dev_addr: Address = i_am.pduSource
        dev_id: ObjectIdentifier = i_am.iAmDeviceIdentifier
        dev_inst = dev_id[1]
        vendor_info = get_vendor_info(i_am.vendorID)

        logger.info("RDF scan: device %s @ %s", dev_inst, dev_addr)
        dev_graph = bacnet_graph.create_device(dev_addr, dev_id)

        try:
            dev_name = await app.read_property(dev_addr, dev_id, "object-name")
            dev_desc = await app.read_property(dev_addr, dev_id, "description")
            setattr(dev_graph, "object-name", dev_name)
            setattr(dev_graph, "description", dev_desc)
        except Exception:
            pass

        obj_list = await _get_object_list_robust(dev_addr, dev_id)
        if not obj_list:
            continue

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
                    val = await app.read_property(dev_addr, obj_id, prop_name)
                    setattr(obj_proxy, prop_name, val)
                except (AbortPDU, ErrorRejectAbortNack, AttributeError):
                    continue
                except Exception as e:
                    logger.debug("Read %s %s: %s", obj_id, prop_name, e)

            total_objects += 1

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
