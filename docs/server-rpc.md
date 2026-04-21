---
title: Server RPC
nav_order: 6
---

# Server RPC (hosted points)

Hosted BACnet objects are created from the **single root CSV** (see [CSV point model](csv-points)). CSV `Name` values map to entries in `point_map`.

For the authoritative JSON-RPC contract (schemas, paths), use the live OpenAPI docs at `http://<edge-host>:8080/docs` on a running gateway.

## Swagger grouping and defaults

- Swagger/OpenAPI groups RPC routes into:
  - **BACnet Server**: hosted point-map read/update endpoints.
  - **BACnet Client**: BACnet network client operations (`whois`, discovery, read/write).
- Default health/discovery RPC route is `POST /server_hello`.

## `server_hello`

- **HTTP:** `POST /server_hello`
- **Params:** `{}`
- **Returns:** `{ "message": "..." }`

## `server_read_all_values`

- **HTTP:** `POST /server_read_all_values`
- **Params:** `{}`
- **Returns:** map of point name → encoded `presentValue`.

Primary server-read RPC for hosted BACnet points.

## `server_read_commandable`

- **HTTP:** `POST /server_read_commandable`
- **Params:** `{}`
- **Returns:** map of **commandable** point names → current value (float / string / int by type).

## `server_update_points`

- **HTTP:** `POST /server_update_points`
- **Params:** `{ "update": { "<point_name>": <value>, ... } }`
- **Behaviour:** updates **non-commandable** server-owned points. **Skips** names in `commandable_point_names`.
- **Returns:** `{ "updated_bacnet_points": { "<name>": "changed from … → …" \| "skipped …" \| "not found" \| "error: …" } }`

Primary server-write RPC for hosted BACnet points.

## `server_read_schedule`

- **HTTP:** `POST /server_read_schedule`
- **Params:** `{ "request": { "name": "<csv-schedule-point-name>" } }`
- **Returns:** `{ "name", "status": "ok"|"not found"|"error", "schedule": { ... } }` when found. `schedule` includes `object_identifier`, `object_name`, `present_value`, `schedule_default`, `weekly_schedule`, `exception_schedule_count`.

## `server_update_schedule`

- **HTTP:** `POST /server_update_schedule`
- **Params:** `{ "update": { "name": "...", "schedule_default": <optional>, "weekly_schedule": [ [ { "time", "value" }, ... ], ... 7 days ... ] } }`
- **Rules:** `weekly_schedule` must have **exactly 7** entries (Monday → Sunday). Times accept `HH:MM` or `HH:MM:SS`.
- **Returns:** `{ "name", "status": "updated", "changed": { ... }, "schedule": { ... } }`
