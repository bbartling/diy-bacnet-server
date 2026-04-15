---
layout: default
title: MQTT
nav_order: 9
---

# MQTT

Two optional MQTT integrations exist; each is gated by environment variables.

## BACnet2MQTT bridge (point state)

Enabled when **`BACNET2MQTT_ENABLED`** is `true`/`1`/`yes` **and** **`MQTT_BROKER_URL`** is set.

| Env | Default | Purpose |
|-----|---------|---------|
| `MQTT_BASE_TOPIC` | `bacnet2mqtt` | Topic prefix. |
| `MQTT_POLL_INTERVAL_SEC` | `30` | Periodic state publish interval. |
| `MQTT_USER` / `MQTT_PASSWORD` | — | Optional broker credentials. |

Topics (prefix = `MQTT_BASE_TOPIC`):

- `{prefix}/bridge/state` — online/offline (retained)
- `{prefix}/bridge/info` — metadata (retained)
- `{prefix}/bridge/devices` — JSON point list (retained)
- `{prefix}/{point_name}` — state JSON (`present_value`, optional `units`)
- `{prefix}/{point_name}/set` — set **non-commandable** points (parsed to number / binary / multistate)

## MQTT RPC gateway (JSON-RPC over pub/sub)

Enabled when **`MQTT_RPC_GATEWAY_ENABLED`** is set and a broker URL is available (`MQTT_RPC_BROKER_URL` or `MQTT_BROKER_URL`).

Default prefix: **`diy-bacnet/gateway`**

| Topic | Role |
|-------|------|
| `{prefix}/cmd` | Subscribe: JSON commands (`method`, `params`, optional `correlation_id` / `id`). |
| `{prefix}/ack` | Publish: ack envelope with `result` or `error`. |
| `{prefix}/telemetry/bridge` | Retained capability manifest (method names, topic strings). |
| `{prefix}/telemetry/status` | Optional periodic status when `MQTT_RPC_TELEMETRY_INTERVAL_SEC` > 0. |

Supported `method` values mirror HTTP JSON-RPC — see **`MQTT_RPC_METHOD_NAMES`** in `bacpypes_server/mqtt_rpc_gateway.py`.
