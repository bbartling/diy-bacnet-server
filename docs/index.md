---
title: Home
nav_order: 1
description: "BACnet/IP + JSON-RPC edge gateway; CSV-hosted points, client operations, optional Modbus and MQTT."
permalink: /
---

# DIY BACnet Server

{: .fs-6 .fw-300 }
Single-process **BACnet/IP** device and **JSON-RPC** HTTP API for lab and edge: CSV point table, BACnet **client** to field devices, optional **Modbus TCP** and **MQTT**.

---

## Quick start

**Repository root** holds one optional gitignored **`.env`** with `BACNET_RPC_API_KEY=…` (Bearer for JSON-RPC and Swagger **Authorize**). Same file for Python and Docker (`--env-file .env`). Do not run `git clone` from inside an existing clone.

### Python (local)

```bash
git clone https://github.com/bbartling/diy-bacnet-server.git
cd diy-bacnet-server
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
printf 'BACNET_RPC_API_KEY=%s\n' "$(openssl rand -hex 32)" > .env
set -a && . ./.env && set +a
python -m bacpypes_server.main --name asdf --instance 123456 --address 192.168.204.18/24:47808 --public --debug
```

### Docker

`--network host` uses the host network stack so BACnet/IP (UDP **47808**) matches bare metal. From another PC use **`http://<LAN-IP>:8080`** and allow **TCP 8080** (and UDP 47808) through the host firewall if needed.

```bash
git clone https://github.com/bbartling/diy-bacnet-server.git
cd diy-bacnet-server
printf 'BACNET_RPC_API_KEY=%s\n' "$(openssl rand -hex 32)" > .env
docker build -t diy-bacnet-server .
docker run --rm -it --network host --env-file .env --name diy-bacnet-gateway diy-bacnet-server \
  python3 -u -m bacpypes_server.main \
  --name asdf --instance 123456 --address 192.168.204.18/24:47808 --public --debug
```

---

## Endpoints (typical)

| What | URL | Notes |
|------|-----|--------|
| **Swagger / OpenAPI** | `http://<host>:8080/docs` | On by default with **`--public`** from `bacpypes_server.main`; override with `BACNET_ENABLE_OPENAPI_DOCS`. |
| **JSON-RPC** | `POST http://<host>:8080/<method>` | With `BACNET_RPC_API_KEY` set, send `Authorization: Bearer` except exempt paths (see [JSON-RPC](json-rpc)). |
| **BACnet/IP** | UDP **47808** | Same process as HTTP; use **`--address`** when multi-homed. |

---

## Documentation

| Section | Description |
|---------|---------------|
| [Getting started](getting-started) | Clone, venv, `.env`, Docker, verify HTTP, firewall, and raw bacpypes3 troubleshooting |
| [BACpypes3 CLI](bacpypes3-cli) | `--name`, `--instance`, `--address`, `--public`, upstream flags |
| [CSV point model](csv-points) | Root CSV, types, commandable points |
| [JSON-RPC](json-rpc) | Paths, Bearer, params shapes |
| [Server RPC](server-rpc) | `server_*` methods |
| [Client BACnet](client-bacnet) | `client_*` methods |
| [Modbus TCP](modbus-tcp) | `POST /modbus/read_registers` |
| [MQTT](mqtt) | BACnet2MQTT, MQTT RPC gateway |
| [Environment](environment) | Environment variables |
| [CI & publishing](ci-and-publishing) | Actions, Pages, PDF, tests |

---

## Philosophy

**BACnet stays in one process.** The same bacpypes3 `Application` hosts CSV objects and performs client work on the OT LAN. Callers use **HTTP + JSON-RPC** (and optionally MQTT); BACnet stays on UDP.

This project is intentionally standalone: use it directly from your own scripts, services, and edge workflows without requiring a specific upstream stack.
