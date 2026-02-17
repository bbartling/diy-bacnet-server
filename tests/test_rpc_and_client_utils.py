import inspect

import pytest

from bacpypes_server.models import DeviceInstanceRange
import bacpypes_server.rpc_methods as rpc_methods
import bacpypes_server.client_utils as client_utils


@pytest.mark.asyncio
async def test_server_hello_direct_call():
    """Directly call the JSON-RPC implementation function.

    This doesn't go through HTTP, but it will fail fast if the
    fastapi-jsonrpc / pydantic models or imports drift.
    """
    result = rpc_methods.server_hello()
    assert isinstance(result, dict)
    assert "message" in result
    assert "BACnet RPC API ready" in result["message"]


def test_rpc_entrypoint_has_methods():
    """Make sure the rpc Entrypoint module exposes the methods we expect.

    Newer fastapi-jsonrpc versions don't expose a `.methods` attribute, so
    we avoid relying on Entrypoint internals and instead look at the
    functions defined in `rpc_methods` that are intended to be RPC calls.
    """
    entrypoint = rpc_methods.rpc

    method_names: set[str] = set()

    # If the Entrypoint *does* expose a collection of methods, use it.
    if hasattr(entrypoint, "methods"):
        try:
            method_names |= set(entrypoint.methods.keys())  # type: ignore[attr-defined]
        except Exception:
            # Don't make the test brittle if the shape is different
            pass

    # Fallback: scan module functions that look like RPC methods
    for name, obj in vars(rpc_methods).items():
        if inspect.iscoroutinefunction(obj) and name.startswith("client_"):
            method_names.add(name)

    for expected in {
        "client_read_property",
        "client_write_property",
        "client_read_multiple",
        "client_whois_range",
        "client_point_discovery",
        "client_read_point_priority_array",
        "client_supervisory_logic_checks",
        "client_whois_router_to_network",
        "client_discovery_to_rdf",
    }:
        assert expected in method_names



@pytest.mark.asyncio
async def test_perform_who_is_wrapper_does_not_crash(monkeypatch):
    """Call the Who-Is helper via RPC, with the underlying bacnet call mocked.

    We don't require a live BACnet network here – only that all of the
    marshaling / error plumbing works with the current bacpypes3 version.
    """

    async def fake_perform_who_is(*args, **kwargs):
        return [{"address": "1.2.3.4", "instance": 1234}]

    # Patch the underlying helper used by the RPC method
    monkeypatch.setattr(
        rpc_methods, "perform_who_is", fake_perform_who_is, raising=True
    )

    req = DeviceInstanceRange(start_instance=0, end_instance=4194303)


    response = await rpc_methods.client_whois_range(req)
    assert response.success is True
    assert isinstance(response.data, dict)
    assert "devices" in response.data
    assert response.data["devices"][0]["instance"] == 1234


def test_client_utils_has_expected_public_api():
    """Simple sanity check that key helper functions exist.

    This gives an early signal if a future refactor deletes or renames
    important helpers that the JSON-RPC layer depends on.
    """
    for func_name in {
        "bacnet_read",
        "bacnet_write",
        "bacnet_rpm",
        "perform_who_is",
    }:
        assert hasattr(client_utils, func_name)
        assert inspect.iscoroutinefunction(getattr(client_utils, func_name))


# --- More RPC methods with mocked BACnet (no live network) ---


@pytest.mark.asyncio
async def test_client_read_property_mocked(monkeypatch):
    """client_read_property with mocked bacnet_read returns result."""
    from bacpypes_server.models import SingleReadRequest

    async def fake_bacnet_read(*args, **kwargs):
        return {"present-value": 72.5}

    monkeypatch.setattr(rpc_methods, "bacnet_read", fake_bacnet_read, raising=True)
    req = SingleReadRequest(
        device_instance=3456789,
        object_identifier="analog-value,1",
        property_identifier="present-value",
    )
    result = await rpc_methods.client_read_property(req)
    assert result == {"present-value": 72.5}


@pytest.mark.asyncio
async def test_client_point_discovery_mocked(monkeypatch):
    """client_point_discovery with mocked point_discovery returns devices and objects."""
    from bacpypes_server.models import DeviceInstanceOnly

    async def fake_point_discovery(instance_id: int):
        return {
            "device_instance": instance_id,
            "device_description": "Fake AHU",
            "objects": [
                {"object_identifier": "analog-value,1", "object_name": "AV-1"},
                {"object_identifier": "analog-value,2", "object_name": "SAT-SP"},
            ],
        }

    monkeypatch.setattr(rpc_methods, "point_discovery", fake_point_discovery, raising=True)
    req = DeviceInstanceOnly(device_instance=3456789)
    response = await rpc_methods.client_point_discovery(req)
    assert response.success is True
    assert response.data["device_instance"] == 3456789
    assert len(response.data["objects"]) == 2
    assert response.data["objects"][0]["object_identifier"] == "analog-value,1"