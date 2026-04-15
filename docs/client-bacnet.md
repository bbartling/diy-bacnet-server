---
layout: default
title: Client BACnet
nav_order: 7
---

# Client BACnet (external devices)

The same BACnet **`Application`** that hosts your CSV objects acts as a **client** on the LAN: Who-Is / I-Am, Read Property, Write Property, RPM, etc. Core logic lives in `bacpypes_server/client_utils.py`; JSON-RPC wrappers in `bacpypes_server/rpc_methods.py`.

## Feature matrix

| Feature | RPC method | Notes |
|---------|------------|--------|
| Who-Is range scan | `client_whois_range` | Returns device list (addresses, vendor, max APDU, etc.). |
| Read one property | `client_read_property` | Returns `{ "<property_identifier>": <encoded> }`. |
| Write property (priority / release) | `client_write_property` | JSON **`null`** or **`"null"`** + **priority** to release a slot. |
| Read Property Multiple | `client_read_multiple` | Chunked internally (**25** object/property pairs per chunk). |
| Object list + names + commandable heuristic | `client_point_discovery` | `object-list`, RPM for `object-name` and `priority-array`. |
| Priority array (one object) | `client_read_point_priority_array` | List of `{ priority_level, type, value }`. |
| Supervisory-style summary | `client_supervisory_logic_checks` | Commandable points and override slots from RPM. |
| Who-Is-Router-To-Network | `client_whois_router_to_network` | Router / network list from the stack NSE. |

## `client_whois_range`

- **Params:** `{ "request": { "start_instance": 1, "end_instance": 3456799 } }` (defaults match Open-FDD style scans.)
- **Returns:** `BaseResponse` with `data.devices`.

## `client_read_property`

- **Params:** `{ "request": { "device_instance": 123456, "object_identifier": "analog-value,1", "property_identifier": "present-value" } }`
- **Object identifier:** e.g. `analog-value,1` (validated against BACpypes3 `ObjectType`).
- **Returns:** single-key dict with encoded value.

## `client_write_property`

- **Params:** `{ "request": { "device_instance", "object_identifier", "property_identifier", "value", "priority": <optional 1–16> } }`
- **Release:** `"value": null` or `"value": "null"` with the same **priority** to release.
- **Returns:** `{ "status": "success", "response": "..." }` on success.

## `client_read_multiple`

- **Params:** `{ "request": { "device_instance": 123456, "requests": [ { "object_identifier", "property_identifier" }, ... ] } }`
- **Returns:** `BaseResponse` with `data.results`: list of `{ object_identifier, property_identifier, property_array_index, value }` (value may be an error string per object/property).

## `client_point_discovery`

- **Params:** `{ "instance": { "device_instance": 987654 } }`
- **Returns:** `BaseResponse` with `data` including `device_address`, `device_instance`, `objects`: `[ { "object_identifier", "name", "commandable" }, ... ]`.

## `client_supervisory_logic_checks`

- **Params:** `{ "instance": { "device_instance": 987654 } }`
- **Returns:** `SupervisorySummary`-compatible dict: `device_id`, `address`, `points`, `points_with_overrides`, `summary`.

## `client_read_point_priority_array`

- **Params:** `{ "request": { "device_instance", "object_identifier" } }`
- **Returns:** **array** of priority slots (not wrapped in `BaseResponse`).

## `client_whois_router_to_network`

- **Params:** `{}`
- **Returns:** `BaseResponse` with `data.routers`.
