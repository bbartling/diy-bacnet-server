---
title: Environment
nav_order: 10
---

# Environment variables

| Variable | Purpose |
|----------|---------|
| `BACNET_RPC_API_KEY` | If set, require `Authorization: Bearer` on protected HTTP routes. |
| `BACNET_ENABLE_OPENAPI_DOCS` | If `1` / `true` / `yes`, expose `/docs`, `/redoc`, `/openapi.json` and exempt them from Bearer in the auth middleware. When unset, `python -m bacpypes_server.main` sets this from **`--public`**. |
| `BACNET_SWAGGER_SERVERS_URL` | Optional OpenAPI `servers` URL (e.g. when the API is behind a path like `/bacnet` on a reverse proxy). |
| `BACNET_NAME` | Docker entrypoint default BACnet **device name** when not passing a full CLI. |
| `BACNET_INSTANCE` | Docker entrypoint default **device instance** number. |
| `BACNET_BIND_ADDRESS` | BACnet/IP bind passed as `--address` (e.g. `192.168.1.10/24:47808`). |
| `BACNET_HTTP_PUBLIC` | If `0` / `false` / `no` (trimmed, case-insensitive), entrypoint omits `--public` (loopback-only HTTP). |
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

## Bearer token notes

- Keep `BACNET_RPC_API_KEY` set for any non-trivial deployment (LAN/edge/shared host).
- The same key value is used by:
  - direct HTTP clients sending `Authorization: Bearer <key>`
  - Swagger **Authorize** in `/docs`
  - any external service that proxies/forwards requests into this gateway
- `POST /server_hello` remains exempt so health/reachability checks can run without a token.
