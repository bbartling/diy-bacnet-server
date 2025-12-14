## 🚀 diy-bacnet-server


![Swagger UI](https://github.com/bbartling/diy-bacnet-server/blob/develop/snip.png)


This project provides a lightweight **BACnet/IP server** with a **JSON-RPC API**, designed to run cleanly as a **single Docker container** during development and early deployment.

The server:

* Loads BACnet points from a **CSV file at startup**
* Exposes BACnet/IP over **UDP 47808**
* Exposes JSON-RPC / Swagger UI over **HTTP 8080**
* Uses **FastAPI + Uvicorn + bacpypes3**

> Docker Compose is intentionally **not used** at this stage.
> It will be introduced later only when orchestrating multiple containers (test clients, simulators, etc.).

---

## 📦 Prerequisites

* Docker Desktop (Windows / macOS / Linux)
* Docker Engine ≥ 20.x

Verify:

```bash
docker version
```

---

## 📂 Project Expectations

Your repository should include:

```text
Dockerfile
requirements.txt
bacpypes_server/
csv_file/
  hvac_server_points.csv
```

BACnet points are defined **only** by the CSV file at startup.

---

## 🔧 Build the Docker Image

From the project root:

```bash
docker build -t diy-bacnet-server .
```

Run the BACnet Server as test:

```bash
docker run --rm -it \
  --network host \
  --name bens-bacnet \
  diy-bacnet-server \
  python3 -u bacpypes_server/main.py \
    --name BensServer \
    --instance 123456 \
    --debug \
    --public

```

How to run "Long Term" (Production Mode)

```bash
docker run -d \
  --restart unless-stopped \
  --network host \
  --name bens-bacnet \
  diy-bacnet-server \
  python3 -u bacpypes_server/main.py \
    --name BensServer \
    --instance 123456 \
    --debug \
    --public
```

---

### Docker Args

Use `--public` only when external access is required.
Without it, the API binds to localhost for safety.

Use `--network host` when running this container because **BACnet/IP relies on UDP broadcast and direct interface binding**, which Docker’s default bridged/NAT networking breaks. Host networking makes the container share the host’s network stack so the BACnet server behaves like a real field device on the LAN and discovery (Who-Is / I-Am) works correctly.

Use `-d` (Detached mode) instead of `-it` to run the container in the background. This allows the BACnet server to operate as a silent daemon service that **does not take over your terminal window**, freeing up your shell for other tasks while the server runs.

Remove `--rm` so the container persists after stopping. Keeping the container allows you to **inspect logs after a crash or restart the same instance later**, whereas `--rm` would immediately delete the container and its history the moment it exits.

Remove `-it` because background services do not require an interactive terminal. Since no user is physically typing into the container console, allocating a pseudo-TTY is unnecessary for a long-running automation service.

Use `--restart unless-stopped` to ensure reliability. This tells Docker to **automatically restart the container** if the application crashes or if the host device reboots, ensuring your BACnet server comes back online without manual intervention.

---

Dev workflow
```bash
docker ps
docker stop bens-bacnet
docker rm bens-bacnet

docker start bens-bacnet
docker logs -f bens-bacnet

```

Full Docker Cleanup (⚠️ Destructive)

Removes unused containers, images, and networks:

```bash
docker system prune -f
```

Remove **everything** (including volumes):

```bash
docker system prune -a --volumes
```

---

## Verifying the API

JSON-RPC API Overview

This server exposes a **JSON-RPC API** (not REST) for interacting with the BACnet/IP server.
The API is primarily intended for **supervisory logic**, testing, and integration with other services.

### Swagger UI

Open in a browser:

```text
http://localhost:8080/docs
```

### OpenAPI JSON

```bash
curl http://localhost:8080/openapi.json
```

---

## 🔄 Workflow: Updating Sensor Data On BACnet Server

This workflow demonstrates how to initialize the server with default values and then simulate live sensor readings by updating **read-only** points via the API.

### 1. Define Points in CSV

Configure your server points in `hvac_server_points.csv`.

  * Use `Commandable,Y` for points controlled by BACnet clients (e.g., setpoints).
  * Use `Commandable,N` for points fed by the API (e.g., sensors).
  * Use the `Default` column to set startup values.

<!-- end list -->

```csv
Name,PointType,Units,Commandable,Default
optimization-enable,BV,Status,Y,active
setpoint-temp,AV,degreesFahrenheit,Y,72.5
outdoor-temp,AV,degreesFahrenheit,N,22.0
```

### 2. Verify Startup Values

Confirm the server loaded the defaults correctly using the `server_read_all_values` endpoint from the Swagger UI.


**Response In Swagger UI**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "optimization-enable": "active",
    "setpoint-temp": 72.5,
    "outdoor-temp": 22.0
  },
  "id": "0"
}
```

### 3. Update Read-Only Point `outdoor-temp`

Use the `server_update_points` method to push new data to non-commandable points.

> **Note:** This method will ingore if you try to update a `Commandable,Y` point (like `setpoint-temp`), as those must be written via BACnet priority arrays.

**Request in Swagger UI**

```bash
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "server_update_points",
  "params": {
    "update": {
      "outdoor-temp": 55.4
    }
  }
}
```

**Response In Swagger UI**

```json
{
  "jsonrpc": "2.0",
  "result": {
    "updated_bacnet_points": {
      "outdoor-temp": "changed from 22.0 → 55.4"
    }
  },
  "id": "1"
}
```


---

## ⚡ Running Without Docker (Optional for testing purposes) 

For direct execution during development:

```bash
python3 bacpypes_server/main.py --name BensServer --instance 123456 --debug
```

To bind publicly (use with care):

```bash
python3 bacpypes_server/main.py --name BensServer --instance 123456 --debug --public
```

By default, the API binds to `127.0.0.1` for safety.

---


## 📜 License

Everything here is **MIT Licensed** — free, open source, and made for the BAS community.  
Use it, remix it, or improve it — just share it forward so others can benefit too. 🥰🌍


【MIT License】

Copyright 2025 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.