---
layout: default
title: Home
nav_order: 1
description: "BACnet/IP + JSON-RPC edge microservice; optional Modbus TCP and MQTT."
permalink: /
---

# DIY BACnet Server

**DIY BACnet Server** is a single-process **BACnet/IP device** plus **JSON-RPC HTTP API** for edge and lab deployments: host a **CSV-defined** point table, push sensor values from agents, act as a **BACnet client** to other controllers on the LAN, and optionally expose **Modbus TCP** reads and **MQTT** (point bridge + JSON-RPC-over-MQTT gateway).

Use it when you want:

- **One UDP socket** for BACnet/IP (`47808`) and **one HTTP port** (`8080`) for automation — no separate “gateway” process unless you choose to split it.
- **JSON-RPC** as the primary contract for both **hosted points** and **client** operations (Who-Is, read/write, RPM, discovery, schedules).
- **Docker-first** operation with **`--network host`** so broadcasts and binding behave like a real edge device.

---

## Where to go next

| I want to… | Read |
|------------|------|
| Install, run locally, Docker, first HTTP check | [Getting started](getting-started.html) |
| Device name, instance, `--address`, BBMD, `--public` | [BACpypes3 CLI](bacpypes3-cli.html) |
| CSV columns, point types, commandable vs server-owned | [CSV point model](csv-points.html) |
| JSON-RPC paths, Bearer auth, params wrappers | [JSON-RPC](json-rpc.html) |
| `server_*` methods (points, schedules) | [Server RPC](server-rpc.html) |
| `client_*` BACnet operations on external devices | [Client BACnet](client-bacnet.html) |
| Utility meters / `POST /modbus/read_registers` | [Modbus TCP](modbus-tcp.html) |
| BACnet2MQTT topics + MQTT RPC gateway | [MQTT](mqtt.html) |
| All environment variables in one table | [Environment](environment.html) |
| CI, GitHub Pages, PDF bundle, local tests | [CI & publishing](ci-and-publishing.html) |

---

## Philosophy

**BACnet stays in one process.** The same BACpypes3 `Application` hosts your CSV objects *and* performs client reads/writes on the OT LAN. Agents speak **HTTP + JSON** (and optionally MQTT); BACnet stays on UDP where it belongs.

**Contracts are explicit.** Params shapes differ per method (`request`, `instance`, `update`, or empty) — use OpenAPI at `/openapi.json` when enabled, or the pages above, and always log JSON-RPC `error` payloads on failure.
