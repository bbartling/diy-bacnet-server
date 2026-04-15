# DIY BACnet Server Documentation

Comprehensive reference for `diy-bacnet-server`: architecture, deployment, API usage, MQTT topics, CSV schema, BACnet client methods, and operations.

---

## Overview

`diy-bacnet-server` is a BACnet/IP + JSON-RPC microservice for Docker-based edge deployments.

- BACnet/IP server on UDP `47808`
- JSON-RPC API on HTTP `8080`
- CSV-defined hosted BACnet objects
- BACnet client helpers for external device discovery/read/write
- Optional MQTT bridge and MQTT RPC gateway
- Optional Modbus TCP read endpoint

---

## Quick Architecture

- **Server side (hosted points):**
  - Loads `*.csv` at startup and creates local BACnet objects
  - Supports AI/AO/AV/BI/BO/BV/MSI/MSO/MSV/Schedule
  - Exposes server methods: `server_hello`, `server_read_all_values`, `server_update_points`, schedule read/update
- **Client side (external BACnet devices):**
  - Who-Is scans, read-property, write-property, RPM, priority-array, discovery, supervisory checks
- **HTTP contract:**
  - JSON-RPC payloads at method paths
  - Swagger/OpenAPI available when enabled

---

## Networking and Runtime

- Run container with `--network host` for BACnet/IP broadcast behavior.
- On multi-NIC hosts, bind BACnet to a specific interface with `--address <ip>/<cidr>[:port]`.
- API binds to `127.0.0.1` by default; use `--public` for `0.0.0.0`.

Example:

```bash
python3 -m bacpypes_server.main --name MyServer --instance 123456 --debug --public
```

---

## API Authentication

When `BACNET_RPC_API_KEY` is set:

- RPC methods require `Authorization: Bearer <key>`
- `POST /server_hello` remains open for basic health checks
- Docs/schema endpoints stay open (`/`, `/docs`, `/redoc`, `/openapi.json`)

When the variable is unset/empty, bearer auth is not enforced.

---

## CSV Point Model

CSV columns:

- `Name`
- `PointType`
- `Units`
- `Commandable`
- `Default`
- optional `States` for MSI/MSO/MSV

Current sample:

```csv
Name,PointType,Units,Commandable,Default
optimization-enable,BV,Status,Y,active
occupancy-schedule,Schedule,Status,N,0
web-weather-dry-bulb,AV,degreesFahrenheit,N,22.0
web-weather-relative-humidity,AV,percent,N,45.0
web-weather-dew-point,AV,degreesFahrenheit,N,12.0
```

Supported `PointType` values:

- `AI`, `AO`, `AV`
- `BI`, `BO`, `BV`
- `MSI`, `MSO`, `MSV`
- `Schedule`

Notes:

- `Commandable=Y` points are intended for BACnet priority-array control.
- `server_update_points` is intended for `Commandable=N` points.
- Schedule points are hosted as BACnet `ScheduleObject`; schedule read/update is available over server RPC.

---

## JSON-RPC Method Catalog

### Server methods

- `server_hello`
- `server_read_all_values`
- `server_read_commandable`
- `server_update_points`
- `server_read_schedule`
- `server_update_schedule`

### Client methods

- `client_whois_range`
- `client_whois_router_to_network`
- `client_read_property`
- `client_write_property`
- `client_read_multiple`
- `client_point_discovery`
- `client_supervisory_logic_checks`
- `client_read_point_priority_array`

---

## Schedule RPC

### Read hosted schedule

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "server_read_schedule",
  "params": {
    "request": {
      "name": "occupancy-schedule"
    }
  }
}
```

### Update hosted schedule

```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "server_update_schedule",
  "params": {
    "update": {
      "name": "occupancy-schedule",
      "schedule_default": 0,
      "weekly_schedule": [
        [{"time": "08:00:00", "value": 1}, {"time": "17:00:00", "value": 0}],
        [{"time": "08:00:00", "value": 1}, {"time": "17:00:00", "value": 0}],
        [{"time": "08:00:00", "value": 1}, {"time": "17:00:00", "value": 0}],
        [{"time": "08:00:00", "value": 1}, {"time": "17:00:00", "value": 0}],
        [{"time": "08:00:00", "value": 1}, {"time": "17:00:00", "value": 0}],
        [{"time": "00:00:00", "value": 0}],
        [{"time": "00:00:00", "value": 0}]
      ]
    }
  }
}
```

---

## MQTT Schema

## MQTT RPC Gateway (recommended)

Default topic prefix: `diy-bacnet/gateway`

- `diy-bacnet/gateway/cmd` (publish commands)
- `diy-bacnet/gateway/ack` (responses/acks)
- `diy-bacnet/gateway/telemetry/bridge` (capabilities manifest, retained)
- `diy-bacnet/gateway/telemetry/status` (optional periodic telemetry)

Command payload shape:

```json
{
  "correlation_id": "1",
  "method": "server_hello",
  "params": {}
}
```

Ack payload shape:

```json
{
  "type": "mqtt_rpc_ack",
  "correlation_id": "1",
  "method": "server_hello",
  "ts_ms": 1710000000000,
  "status": "ok",
  "result": {
    "message": "BACnet RPC API ready. Interactive docs are disabled; use Open-FDD BACnet tools or JSON-RPC."
  }
}
```

---

## BACnet2MQTT Bridge (optional)

Default base topic: `bacnet2mqtt`

- `bacnet2mqtt/bridge/state` (retained)
- `bacnet2mqtt/bridge/info` (retained)
- `bacnet2mqtt/bridge/devices` (retained)
- `bacnet2mqtt/<point_name>` (state JSON)
- `bacnet2mqtt/<point_name>/set` (set payload)

This bridge is primarily point state mirroring. For command/response workflows, use MQTT RPC gateway.

---

## Modbus TCP Endpoint

Endpoint: `POST /modbus/read_registers`

Features:

- `holding` or `input` reads
- batched register ops
- decode options: `uint16`, `int16`, `uint32`, `int32`, `float32`
- optional `scale` and `offset`

`pyModbusTCP` must be available in the runtime environment.

---

## Docker Run Examples

Build:

```bash
docker build -t diy-bacnet-server .
```

Run (interactive):

```bash
docker run --rm -it --network host --name bens-bacnet diy-bacnet-server \
  python3 -m bacpypes_server.main --name BensServer --instance 123456 --debug --public
```

Run (long-term):

```bash
docker run -d --restart unless-stopped --network host --name bens-bacnet diy-bacnet-server \
  python3 -m bacpypes_server.main --name BensServer --instance 123456 --debug --public
```

---

## Testing

Run tests:

```bash
python3 -m venv env
. ./env/bin/activate
pip install -r requirements.txt
pytest tests/ -v
```

Core coverage includes:

- RPC method parsing/contract
- BACnet helper behavior (mocked)
- MQTT bridge and MQTT RPC gateway
- CSV/model validation
- schedule method read/update paths

---

## License

MIT License. See `LICENSE`.
