---
title: BACpypes3 CLI
nav_order: 3
---

# BACpypes3 CLI

The process subclasses **`bacpypes3.argparse.SimpleArgumentParser`** and adds **`--public`** (this repository only). All other device and stack options come from BACpypes3.

Print the full upstream parser help locally:

```bash
python -c "from bacpypes3.argparse import SimpleArgumentParser; SimpleArgumentParser().print_help()"
```

## Standard BACpypes3 options (summary)

| Option | Purpose |
|--------|---------|
| `-h`, `--help` | Show help and exit. |
| `--loggers` | List debugging logger names. |
| `--debug [LOGGER ...]` | Attach debug handlers to loggers (optional logger names). |
| `--color` | Colorized debug output. |
| `--route-aware` | Enable route-aware behaviour where supported. |
| `--name NAME` | BACnet **device name** (string). |
| `--instance INSTANCE` | BACnet **device object instance** (device identifier). |
| `--network NETWORK` | Local **network number** when applicable. |
| `--address ADDRESS` | **Bind address** for BACnet/IP, e.g. `192.168.1.50/24:47808` or `0.0.0.0:47808`. On **multi-homed** gateways, set this to the **OT / BAS** interface. |
| `--vendoridentifier VENDORIDENTIFIER` | BACnet **Vendor ID** for the device. |
| `--foreign FOREIGN` | **Foreign device** BBMD registration address (when using BBMD). |
| `--ttl TTL` | **Time-to-live** for foreign device registration (seconds). |
| `--bbmd BBMD [BBMD ...]` | **BDT / BBMD** address list for BACnet/IP with BBMDs. |

## This repository’s extra flag

| Option | Purpose |
|--------|---------|
| `--public` | Bind **HTTP** to `0.0.0.0` instead of `127.0.0.1`. By default also enables **`/docs`** when `BACNET_ENABLE_OPENAPI_DOCS` is unset (see [Environment](environment)). BACnet UDP still follows **`--address`**. |

## Recommended examples

**Bind BACnet to a specific interface (multi-NIC edge):**

```bash
python -m bacpypes_server.main \
  --name EdgeGateway \
  --instance 123456 \
  --address 192.168.10.50/24:47808 \
  --debug \
  --public
```

**Local laptop (no remote API exposure):**

```bash
python -m bacpypes_server.main --name Lab --instance 999 --debug
```
