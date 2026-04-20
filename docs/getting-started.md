---
title: Getting started
nav_order: 2
---

# Getting started

This page matches the **[README](https://github.com/bbartling/diy-bacnet-server/blob/main/README.md)** quick start: clone once, **`.env`** in the **repository root**, then Python or Docker.

---

## Prerequisites

- **Python 3.12+** for local runs, or **Docker** for container runs.
- **Git** (only for first clone).
- **`openssl`** (or generate a random secret another way) for `BACNET_RPC_API_KEY`.

---

## Clone and venv (Python)

If you are **already** inside a clone, skip `git clone` / `cd` (running clone again nests a second repo).

```bash
git clone https://github.com/bbartling/diy-bacnet-server.git
cd diy-bacnet-server
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -e ".[dev]"
```

---

## Bearer secret (`.env`)

Create **one line** in **`.env`** at the repo root (file is **gitignored**):

```bash
printf 'BACNET_RPC_API_KEY=%s\n' "$(openssl rand -hex 32)" > .env
```

Load it into your shell for local runs:

```bash
set -a && . ./.env && set +a
```

Skip this section only for **unsecured loopback** experiments.

---

## Run from source

Use **`python -m bacpypes_server.main`** so imports match Docker.

```bash
python -m bacpypes_server.main --name asdf --instance 123456 --address 192.168.204.18/24:47808 --public --debug
```

- **Without `--public`**: HTTP on **`127.0.0.1:8080`** only; by default **no `/docs`** (unless you set `BACNET_ENABLE_OPENAPI_DOCS`).
- **With `--public`**: HTTP on **`0.0.0.0:8080`**; **`/docs`** on by default unless `BACNET_ENABLE_OPENAPI_DOCS` is set to override.

Omit **`--address …`** if a single NIC is enough (bacpypes3 picks it). See [BACpypes3 CLI](bacpypes3-cli) for BBMD and other upstream flags.

---

## Docker

`--network host` puts the container on the **host’s** IP stack so BACnet/IP behaves like bare metal.

```bash
docker build -t diy-bacnet-server .
docker run --rm -it --network host --env-file .env --name diy-bacnet-gateway diy-bacnet-server \
  python3 -u -m bacpypes_server.main \
  --name asdf --instance 123456 --address 192.168.204.18/24:47808 --public --debug
```

`--env-file .env` reads **`BACNET_RPC_API_KEY`** from the **host** path next to your `Dockerfile`.

---

## Verify HTTP

- **`POST /server_hello`** — minimal JSON-RPC check (no Bearer required). See [JSON-RPC](json-rpc).
- **`GET /docs`** — when enabled, Swagger UI; **Authorize** uses the same value as **`BACNET_RPC_API_KEY`**.

From another machine on the LAN, use **`http://<server-LAN-IP>:8080/docs`**, not `127.0.0.1`. Ensure the host firewall allows **TCP 8080** (and **UDP 47808** for BACnet).

---

## CSV location

Exactly **one** `*.csv` in the **repository root** (e.g. `hvac_server_points.csv`). See [CSV point model](csv-points).

---

## Quick test (raw bacpypes3 troubleshooting)

Use this mini bacpypes3-only console test when you want to isolate BACnet/IP behavior from the full FastAPI gateway.

```bash
# Create virtual environment
python -m venv env

# Activate (Linux / macOS)
. env/bin/activate

# Install dependencies
pip install bacpypes3 ifaddr
```

Run a minimal bacpypes3 instance:

```bash
python -m bacpypes3 \
  --name BensRawBacpypes3Test \
  --address 192.168.204.12/24 \
  --instance 123456 \
  --debug
```

You can then use the interactive commands:

```text
> help
commands: config, exit, help, iam, ihave, irt, rbdt, read, rfdt, rpm, wbdt, whohas, whois, wirtn, write
```

```text
> whois
```

Example output (trimmed):

```text
3456788 192.168.204.16
3456789 192.168.204.13
3456790 192.168.204.14
```

Common commands:

```bash
# Discover devices in a range
whois 1000 3456799

# Read a point
read 192.168.204.13 analog-input,1 present-value

# Write a value (priority 9)
write 192.168.204.14 analog-output,1 present-value 999.8 9

# Release a command (null write)
write 192.168.204.14 analog-output,1 present-value null 9
```

### Important host-level warning

Only one BACnet service should bind on the same host/port at a time. Before starting this raw bacpypes3 console, stop other BACnet apps on the OS that may already be bound (for example the DIY BACnet server process/container).
