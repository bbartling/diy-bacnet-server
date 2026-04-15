---
layout: default
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

## Supported `PointType` codes

`AI`, `AO`, `AV`, `BI`, `BO`, `BV`, `MSI`, `MSO`, `MSV`, `Schedule`

## Behaviour

- **`Commandable=Y`:** Intended for BACnet writes (priority arrays, supervisory logic). **Do not** push these via `server_update_points` — the server skips them to avoid fighting BACnet clients.
- **`Commandable=N`:** **Server-owned** values (sensors, weather feeds, etc.). Agents update these with **`server_update_points`**.

## Schedule rows

`Schedule` creates a BACnet **`ScheduleObject`** with a default weekly pattern from the loader. Read/update the structured schedule over **`server_read_schedule`** / **`server_update_schedule`** (see [Server RPC](server-rpc.html)).

**Note:** BACpypes3’s local schedule interpreter may have timing quirks in some versions; validate schedule behaviour on a lab controller for production calendars.
