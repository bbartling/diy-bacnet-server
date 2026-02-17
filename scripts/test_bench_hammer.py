#!/usr/bin/env python3
"""
Test-bench hammer: exercise diy-bacnet-server JSON-RPC routes (except client_whois_router_to_network).

Covers: server_hello, client_whois_range, client_read_property, client_read_multiple,
client_write_property (write + release null), client_read_point_priority_array, client_point_discovery.

Usage:
  python scripts/test_bench_hammer.py --base-url http://192.168.204.16:8080
  python scripts/test_bench_hammer.py --base-url http://localhost:8080 --device 3456789
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

try:
    import requests
except ImportError:
    print("pip install requests", file=sys.stderr)
    sys.exit(1)

DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_DEVICE = 3456789
# Object IDs that typically exist on fake AHU (fake_ahu.py): analog-value,1 and analog-value,2
DEFAULT_READ_OID = "analog-value,1"
DEFAULT_WRITE_OID = "analog-value,2"  # commandable; use for write / release
DEFAULT_PRIORITY = 8


def rpc_call(
    base_url: str, method: str, params: dict[str, Any], id_: str = "0"
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/{method}"
    payload = {"jsonrpc": "2.0", "id": id_, "method": method, "params": params}
    resp = requests.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def run_server_hello(base_url: str) -> None:
    print("\n=== server_hello ===")
    data = rpc_call(base_url, "server_hello", {})
    print(json.dumps(data, indent=2))
    if "result" in data:
        print("  OK")
    else:
        print("  (unexpected response)")


def run_client_whois_range(base_url: str, start: int = 1, end: int = 3456800) -> None:
    print("\n=== client_whois_range ===")
    params = {"request": {"start_instance": start, "end_instance": end}}
    data = rpc_call(base_url, "client_whois_range", params)
    print(json.dumps(data, indent=2))
    if "result" in data and data["result"].get("data", {}).get("devices"):
        print(f"  OK — {len(data['result']['data']['devices'])} device(s)")
    elif "error" in data:
        print("  ERROR (no devices or Who-Is failure)")
    else:
        print("  OK")


def run_client_read_property(
    base_url: str, device_instance: int, object_identifier: str, property_id: str = "present-value"
) -> None:
    print("\n=== client_read_property ===")
    params = {
        "request": {
            "device_instance": device_instance,
            "object_identifier": object_identifier,
            "property_identifier": property_id,
        }
    }
    data = rpc_call(base_url, "client_read_property", params)
    print(json.dumps(data, indent=2))
    if "result" in data:
        print("  OK")
    else:
        print("  ERROR")


def run_client_read_multiple(
    base_url: str, device_instance: int, requests_list: list[dict[str, str]]
) -> None:
    print("\n=== client_read_multiple ===")
    params = {"request": {"device_instance": device_instance, "requests": requests_list}}
    data = rpc_call(base_url, "client_read_multiple", params)
    print(json.dumps(data, indent=2))
    if "result" in data and data["result"].get("data", {}).get("results") is not None:
        print("  OK")
    else:
        print("  ERROR or no results")


def run_client_write_property(
    base_url: str,
    device_instance: int,
    object_identifier: str,
    value: float | int | str,
    property_id: str = "present-value",
    priority: int | None = DEFAULT_PRIORITY,
) -> None:
    print("\n=== client_write_property (write) ===")
    request: dict[str, Any] = {
        "device_instance": device_instance,
        "object_identifier": object_identifier,
        "property_identifier": property_id,
        "value": value,
    }
    if priority is not None:
        request["priority"] = priority
    data = rpc_call(base_url, "client_write_property", {"request": request})
    print(json.dumps(data, indent=2))
    if "result" in data:
        print("  OK")
    else:
        print("  ERROR")


def run_client_write_release_null(
    base_url: str,
    device_instance: int,
    object_identifier: str,
    priority: int = DEFAULT_PRIORITY,
    property_id: str = "present-value",
) -> None:
    print("\n=== client_write_property (release null) ===")
    params = {
        "request": {
            "device_instance": device_instance,
            "object_identifier": object_identifier,
            "property_identifier": property_id,
            "value": "null",
            "priority": priority,
        }
    }
    data = rpc_call(base_url, "client_write_property", params)
    print(json.dumps(data, indent=2))
    if "result" in data:
        print("  OK")
    else:
        print("  ERROR")


def run_client_read_point_priority_array(
    base_url: str, device_instance: int, object_identifier: str
) -> None:
    print("\n=== client_read_point_priority_array ===")
    params = {
        "request": {
            "device_instance": device_instance,
            "object_identifier": object_identifier,
        }
    }
    data = rpc_call(base_url, "client_read_point_priority_array", params)
    print(json.dumps(data, indent=2))
    if "result" in data:
        print("  OK")
    else:
        print("  ERROR (object may not support priority-array)")


def run_client_point_discovery(base_url: str, device_instance: int) -> None:
    print("\n=== client_point_discovery ===")
    params = {"instance": {"device_instance": device_instance}}
    data = rpc_call(base_url, "client_point_discovery", params)
    print(json.dumps(data, indent=2))
    if "result" in data and data["result"].get("data"):
        obj_count = len(data["result"]["data"].get("objects", []))
        print(f"  OK — {obj_count} object(s)")
    else:
        print("  ERROR")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hammer diy-bacnet-server RPC routes (whois, read, read mult, write, release null, priority array, point discovery)"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Base URL of diy-bacnet-server (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--device",
        type=int,
        default=DEFAULT_DEVICE,
        help=f"Device instance for read/write/priority/discovery (default: {DEFAULT_DEVICE})",
    )
    parser.add_argument(
        "--read-oid",
        default=DEFAULT_READ_OID,
        help=f"Object identifier for single read (default: {DEFAULT_READ_OID})",
    )
    parser.add_argument(
        "--write-oid",
        default=DEFAULT_WRITE_OID,
        help=f"Object identifier for write/release/priority (default: {DEFAULT_WRITE_OID})",
    )
    parser.add_argument(
        "--whois-end",
        type=int,
        default=3456800,
        help="Who-Is end_instance (default: 3456800)",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")

    print(f"Base URL: {base}")
    print(f"Device instance: {args.device}")

    try:
        run_server_hello(base)
        run_client_whois_range(base, start=1, end=args.whois_end)
        run_client_read_property(base, args.device, args.read_oid)
        run_client_read_multiple(
            base,
            args.device,
            [
                {"object_identifier": args.read_oid, "property_identifier": "present-value"},
                {"object_identifier": args.write_oid, "property_identifier": "present-value"},
            ],
        )
        run_client_write_property(base, args.device, args.write_oid, 55.0, priority=DEFAULT_PRIORITY)
        run_client_read_property(base, args.device, args.write_oid)
        run_client_write_release_null(base, args.device, args.write_oid, priority=DEFAULT_PRIORITY)
        run_client_read_point_priority_array(base, args.device, args.write_oid)
        run_client_point_discovery(base, args.device)
    except requests.RequestException as e:
        print(f"\nRequest failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1

    print("\n=== All routes exercised ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
