---
title: CSV point model
nav_order: 4
---

# CSV point model

Columns:

- **`Name`** — API / friendly name for the point.
- **`PointType`** — BACnet object type code (see below).
- **`Units`** — Engineering units for analog types (resolved via `EngineeringUnits` fuzzy match).
- **`Commandable`** — `Y` or `N`.
- **`Default`** — Startup value.
- **`States`** (optional) — Integer number of states for `MSI` / `MSO` / `MSV` (default 2).
- **`Instance`** (optional, recommended) — BACnet object instance number (`0..4194303`). When omitted, the loader falls back to per-type auto-assignment.
- **`CovIncrement`** (optional, analog only) — BACnet COV increment for `AI` / `AO` / `AV`; must be numeric and `> 0` (default `1.0`).

## Supported `PointType` codes

`AI`, `AO`, `AV`, `BI`, `BO`, `BV`, `MSI`, `MSO`, `MSV`, `Schedule`

## Behaviour

- **`Commandable=Y`:** Intended for BACnet writes (priority arrays, supervisory logic). **Do not** push these via `server_update_points` — the server skips them to avoid fighting BACnet clients.
- **`Commandable=N`:** **Server-owned** values (sensors, weather feeds, etc.). Agents update these with **`server_update_points`**.
- **Instance stability:** Use explicit `Instance` values to keep object identifiers stable across CSV row reordering and future point additions.
- **Duplicate identifiers:** Rows that collide on `(object-type, Instance)` are skipped with an error log so object identity stays deterministic.

## Schedule rows

`Schedule` creates a BACnet **`ScheduleObject`** with a default weekly pattern from the loader. Read/update the structured schedule over **`server_read_schedule`** / **`server_update_schedule`** (see [Server RPC](server-rpc)).

**Note:** BACpypes3’s local schedule interpreter may have timing quirks in some versions; validate schedule behaviour on a lab controller for production calendars.
