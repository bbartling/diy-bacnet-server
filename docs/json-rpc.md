---
title: JSON-RPC
nav_order: 5
---

# JSON-RPC

## Endpoint shape

`fastapi-jsonrpc` exposes **one HTTP route per method**. The path is **`POST /<method_name>`** (the entrypoint uses an empty prefix in code).

Example: `POST http://localhost:8080/server_hello`

## Request envelope

```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "server_hello",
  "params": {}
}
```

The HTTP path already selects the handler; some clients still send `"method"` in the body — follow OpenAPI / your generator.

## Bearer auth (`BACNET_RPC_API_KEY`)

When **`BACNET_RPC_API_KEY`** is set:

- Send **`Authorization: Bearer <key>`** on protected routes.
- **Exempt** without Bearer: `GET /`, `POST /server_hello`.
- When **`/docs`** is enabled (same as **`--public`** when using `bacpypes_server.main`, unless configured otherwise), these are also exempt so the UI can load: `/docs`, `/redoc`, `/openapi.json` (and static paths under them).
- If another application or gateway proxy calls this server, it should forward the same Bearer value on protected routes.

When the key is **unset** or **empty**, Bearer auth is not enforced.

## Params wrappers (do not assume one shape)

| Pattern | Methods |
|---------|---------|
| `params.request` | `client_read_property`, `client_write_property`, `client_read_multiple`, `client_whois_range`, `client_read_point_priority_array`, `server_read_schedule` |
| `params.instance` | `client_point_discovery`, `client_supervisory_logic_checks` |
| `params.update` | `server_update_points`, `server_update_schedule` |
| `{}` or omit | `server_hello`, `server_read_all_values`, `server_read_commandable`, `client_whois_router_to_network` |

## Response shapes

- Many client methods return **`{ success, message, data }`** (`BaseResponse`).
- Some return a **plain dict** or **list** (e.g. `client_read_point_priority_array` returns a list of slot dicts).
- Always log the full JSON-RPC **`error`** object on failure (`code`, `message`, optional `data`).

## Modbus is not JSON-RPC

**`POST /modbus/read_registers`** is a normal FastAPI route, not the JSON-RPC router. See [Modbus TCP](modbus-tcp).
