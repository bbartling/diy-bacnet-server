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

This creates a reusable image named `diy-bacnet-server`.

---

## ▶️ Run the BACnet Server

### Standard Run (recommended)

```bash
docker run -d \
  --name bens-bacnet \
  -p 47808:47808/udp \
  -p 8080:8080 \
  diy-bacnet-server
```

This:

* Starts the BACnet/IP server
* Loads points from the CSV file
* Exposes Swagger UI at
  👉 **[http://localhost:8080/docs](http://localhost:8080/docs)**

---

### Run With Explicit CLI Arguments

You may override the default command:

```bash
docker run -d \
  --name bens-bacnet \
  -p 47808:47808/udp \
  -p 8080:8080 \
  diy-bacnet-server \
  python3 -u bacpypes_server/main.py \
    --name BensServer \
    --instance 123456 \
    --debug \
    --public
```

Use `--public` only when external access is required.
Without it, the API binds to localhost for safety.

---

## 📋 Viewing Logs

### Follow logs live

```bash
docker logs -f bens-bacnet
```

### View logs once

```bash
docker logs bens-bacnet
```

> Tip: run without `-d` to see logs directly in your terminal:

```bash
docker run -it --name bens-bacnet ...
```

---

## 🌐 Verifying the API

### Swagger UI

Open in a browser:

```text
http://localhost:8080/docs
```

### OpenAPI JSON

```bash
curl http://localhost:8080/openapi.json
```

A valid JSON response confirms the API is healthy.

---

## 🧹 Stop & Clean Up

### Stop the container

```bash
docker stop bens-bacnet
```

### Remove the container

```bash
docker rm bens-bacnet
```

---

## 🔄 Rebuild & Redeploy (Clean Restart)

```bash
docker stop bens-bacnet
docker rm bens-bacnet
docker build -t diy-bacnet-server .
docker run -d \
  --name bens-bacnet \
  -p 47808:47808/udp \
  -p 8080:8080 \
  diy-bacnet-server
```

---

## 🧨 Full Docker Cleanup (⚠️ Destructive)

Removes unused containers, images, and networks:

```bash
docker system prune -f
```

Remove **everything** (including volumes):

```bash
docker system prune -a --volumes
```

---

## 🧪 BACnet Testing

Use any BACnet/IP client tool:

* YABE
* BACnet Discovery Tool
* Other BAS software

The server will respond to:

* Who-Is / I-Am
* ReadProperty
* WriteProperty (for commandable points)
* Priority-array logic

---

## 🧠 JSON-RPC API Overview

This server exposes a **JSON-RPC API** (not REST) for interacting with the BACnet/IP server.
The API is primarily intended for **supervisory logic**, testing, and integration with other services.

> 📌 **You do not need to memorize these methods.**
> The full, interactive API documentation is available via Swagger UI.

👉 **[http://localhost:8080/docs](http://localhost:8080/docs)**

---

### What the API is used for

At a high level, the API supports three main workflows:

1. **Managing local BACnet server points**

   * Update server-side values
   * Read back commandable vs read-only points
   * Inspect overrides written by external BAS systems

2. **Acting as a BACnet client**

   * Read properties from other BACnet devices
   * Write properties with priority
   * Release overrides
   * Perform Who-Is / I-Am discovery

3. **Supervisory diagnostics**

   * Inspect priority arrays
   * Detect active overrides
   * Discover available points on remote devices

---

## 🔑 Key Concepts

### CSV-Defined Server Points

All BACnet server objects (“points”) are defined **at startup** using a CSV file.

* The CSV defines:

  * object name
  * object type (AV / BV)
  * engineering units
  * whether the point is commandable
* These points become discoverable BACnet objects on the network.
* Commandable points support **priority-array logic**.

---

### Commandable vs Read-Only

* **Commandable points**
  Writable via BACnet (priority-based overrides).
  Typical use: enables, setpoints, supervisory commands.

* **Read-only points**
  Updated via JSON-RPC only.
  Typical use: sensors, calculated values, telemetry.

---

## 🧪 Exploring the API (Recommended Workflow)

1. Start the server
2. Open Swagger UI
   👉 **[http://localhost:8080/docs](http://localhost:8080/docs)**
3. Use the interactive interface to:

   * Inspect available RPC methods
   * Send test requests
   * View responses in real time

Swagger UI is the **authoritative API reference**.

---

## 🧪 BACnet Interoperability Testing

Use any standard BACnet/IP tool:

* YABE
* BACnet Discovery Tool (BDT)
* BAS workstations

The server supports:

* Who-Is / I-Am
* ReadProperty
* WriteProperty
* Priority-array overrides
* Release (null writes)

---

## ⚡ Running Without Docker (Optional)

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