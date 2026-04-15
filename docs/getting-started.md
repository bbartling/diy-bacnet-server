---
layout: default
title: Getting started
nav_order: 2
---

# Getting started

## Clone and Python venv (development)

```bash
git clone https://github.com/bbartling/diy-bacnet-server.git
cd diy-bacnet-server
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Run from source (module entrypoint)

Use **`python -m bacpypes_server.main`** so imports match Docker and the package layout is correct:

```bash
python -m bacpypes_server.main --name BensServer --instance 123456 --debug --public
```

- Without **`--public`**, HTTP listens on **`127.0.0.1:8080`** only.
- With **`--public`**, HTTP listens on **`0.0.0.0:8080`** (use only on trusted networks).

See [BACpypes3 CLI](bacpypes3-cli.html) for `--address`, BBMD, vendor ID, and other stack flags.

## Docker (typical edge)

```bash
docker build -t diy-bacnet-server .
docker run --rm -it --network host --name bens-bacnet diy-bacnet-server \
  python3 -m bacpypes_server.main --name BensServer --instance 123456 --debug --public
```

Use **`--network host`** so BACnet/IP broadcasts and interface binding work; bridged Docker NAT usually breaks discovery.

If the image sets `WORKDIR` / `PYTHONPATH` for `/app`, keep the same `python3 -m bacpypes_server.main` invocation inside the container.

## Verify HTTP

- **Health:** `POST /server_hello` with a JSON-RPC body (see [JSON-RPC](json-rpc.html)).
- **OpenAPI / Swagger:** when `OFDD_ENABLE_OPENAPI_DOCS` is enabled, open `http://<host>:8080/docs` and `/openapi.json`.

## CSV file location

The loader expects **exactly one** `*.csv` in the **repository root** (see `bacpypes_server/server_utils.py`). The example in this repo is `hvac_server_points.csv`. See [CSV point model](csv-points.html).
