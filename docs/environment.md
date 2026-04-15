---
layout: default
title: Environment
nav_order: 10
---

# Environment variables

| Variable | Purpose |
|----------|---------|
| `BACNET_RPC_API_KEY` | If set, require `Authorization: Bearer` on protected HTTP routes. |
| `OFDD_ENABLE_OPENAPI_DOCS` | If set, expose `/docs`, `/redoc`, `/openapi.json` and exempt them from Bearer in the auth middleware. |
| `BACNET2MQTT_ENABLED` | Enable BACnet2MQTT bridge. |
| `MQTT_BROKER_URL` | Broker URL for the bridge (and MQTT RPC gateway fallback). |
| `MQTT_BASE_TOPIC` | Bridge topic prefix. |
| `MQTT_POLL_INTERVAL_SEC` | Bridge poll interval. |
| `MQTT_USER` / `MQTT_PASSWORD` | Broker authentication. |
| `MQTT_RPC_GATEWAY_ENABLED` | Enable MQTT RPC gateway. |
| `MQTT_RPC_BROKER_URL` | Optional separate broker URL for the RPC gateway. |
| `MQTT_RPC_TOPIC_PREFIX` | RPC topic prefix (default `diy-bacnet/gateway`). |
| `MQTT_RPC_TELEMETRY_INTERVAL_SEC` | Telemetry interval; `0` disables periodic `telemetry/status`. |
| `MQTT_RPC_CLIENT_ID` | Optional MQTT client id. |
