# Testing diy-bacnet-server

## What exists

- **test_models.py** — Pydantic request/response validation (no BACnet). DeviceInstanceRange, SingleReadRequest, WritePropertyRequest, ReadMultiple*, ReadPriorityArrayRequest; valid/invalid object_identifier, property_identifier, bounds.
- **test_rpc_and_client_utils.py** — RPC method presence, `server_hello` direct call, `client_whois_range` with mocked `perform_who_is`, `client_read_property` and `client_point_discovery` with mocked BACnet helpers, client_utils public API sanity check.
- **test_rpc_parse_and_contract.py** — `parse_object_identifier` (valid/invalid), HTTP contract for `server_hello` and `client_whois_range` via FastAPI TestClient (no live BACnet).
- **test_docker_bacnet_server.py** — Integration: Docker Compose up, assert container logs show BACnet app and JSON-RPC ready, no tracebacks. Requires Docker.

**Run unit tests (no Docker):**

```bash
pytest tests/ -v -k "not test_docker and not test_bacnet_server"
# or exclude the docker module by name
pytest tests/test_models.py tests/test_rpc_and_client_utils.py tests/test_rpc_parse_and_contract.py -v
```

**Run including Docker integration test:**

```bash
pytest tests/ -v
```

## Ideas for enhancement

1. **More mocked RPC tests** — `client_write_property`, `client_read_multiple`, `client_read_point_priority_array`, `client_supervisory_logic_checks` with `bacnet_write`, `bacnet_rpm`, `read_point_priority_arr` mocked so no live device required.
2. **Error-path tests** — Assert that invalid params return JSON-RPC error (e.g. invalid object_identifier, device not found). Mock `get_device_address` to raise so `client_read_property` returns ReadPropertyError.
3. **Request/response schema tests** — Snapshot or explicit assert on JSON shape for one success response per method (so API contract is documented and regression-checked).
4. **Bench hammer as optional pytest** — In a test that’s skipped unless `BASE_URL` is set, run `test_bench_hammer`-style sequence against a live server (e.g. CI with a fake device container).
5. **Property identifier and object type enums** — Small tests that bacpypes3 `PropertyIdentifier` / `ObjectType` still contain the keys we use in examples (e.g. `present-value`, `analog-value`).
6. **Docker test robustness** — Reduce sleep (or poll for “JSON-RPC API ready” in logs) so CI is faster; optional mark for “needs_docker” so unit-only runs stay fast.

## Dependencies

Unit tests need: `pytest`, `pytest-asyncio`, `httpx` or `requests` (TestClient is from FastAPI). The project may already list these; if not, `pip install pytest pytest-asyncio fastapi` (or the stack used by the app).
