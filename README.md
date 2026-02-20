## 🚀 diy-bacnet-server

![Swagger UI](https://github.com/bbartling/diy-bacnet-server/blob/develop/snip.png)


This project provides a lightweight **BACnet/IP server** with a **JSON-RPC API**, designed to run cleanly as a **single Docker-container microservice** for IoT applications. It also works great as an easy BACnet server deployment for any embedded-Linux project that supports Docker.

The server:

* Loads BACnet points from a **CSV file at startup**
* Exposes BACnet/IP over **UDP 47808**
* Exposes JSON-RPC + Swagger UI over **HTTP 8080**
* Uses **FastAPI + Uvicorn + bacpypes3**


---


## 📦 Prerequisites

* Docker Desktop (Windows / macOS / Linux)
* Docker Engine ≥ 20.x

**Verify Docker Engine:**

```bash
docker version

```

**Verify Docker Compose (V2):**

```bash
docker compose version

```

> **Note:** This project uses the modern `docker compose` command (with a space).

---

### 🛠️ Installation (Raspberry Pi / Linux)

If Docker is not installed, use the official convenience script. This installs both the Docker Engine and the modern Compose plugin automatically:

```bash
# 1. Update system
sudo apt-get update

# 2. Install Docker Engine + Docker Compose V2
curl -sSL [https://get.docker.com](https://get.docker.com) | sh

# 3. Add your user to the docker group (avoids using 'sudo' for every command)
sudo usermod -aG docker $USER

```

> Log out and log back in for the user group changes to take effect.*

---

## 📂 BACnet Server Defined by CSV File

Your repository should include an example CSV file:

```text
Dockerfile
requirements.txt
bacpypes_server/
csv_file/
  hvac_server_points.csv
```

### 📄 CSV Reference Description

This CSV defines the BACnet points that the server will expose. Each row represents a single BACnet object, including its type, engineering units, whether it is commandable, and an optional default value.

Example:

```
Name,PointType,Units,Commandable,Default
optimization-enable,BV,Status,Y,active
setpoint-temp,AV,degreesFahrenheit,Y,72.5
outdoor-temp,AV,degreesFahrenheit,N,22.0
```

---

### 🧠 Column Meanings

**`Name`**
Human-friendly / API name for the BACnet point.

**`PointType`**
BACnet object type:

* `AV` = Analog Value
* `BV` = Binary Value
  (You could extend this later with AI/AO/BI/BO/etc.)

**`Units`**
Engineering units for analog points (e.g., `degreesFahrenheit`, `Status`, `percent`, etc.).

**`Commandable`**
Indicates whether this point can be written to:

* `Y` = Commandable (clients can write / override)
* `N` = Read-only

**`Default`**
Initial value the point is initialized with when the server starts.

---

### 🧾 What these specific rows represent

| Name                | BACnet Type | Meaning                             | Commandable? | Default |
| ------------------- | ----------- | ----------------------------------- | ------------ | ------- |
| optimization-enable | BV          | Enables/disables optimization logic | Yes          | active  |
| setpoint-temp       | AV          | HVAC temperature setpoint           | Yes          | 72.5°F  |
| outdoor-temp        | AV          | Outside air temperature reference   | No           | 22°F    |


> Refer to the Swagger UI for details on how data is read from and written to the BACnet server. Points are updated and retrieved using JSON-RPC POST requests.

---

## 🔧 Build the Docker Image

Clone the repo from GitHub and from the project root:

```bash
docker build -t diy-bacnet-server .
```

Run the BACnet Server as test:

```bash
docker run --rm -it \
  --network host \
  --name bens-bacnet \
  diy-bacnet-server \
  python3 -m bacpypes_server.main \
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
  python3 -m bacpypes_server.main \
    --name BensServer \
    --instance 123456 \
    --debug \
    --public
```

---

### Docker Args

Use `--public` only when external access is required.
Without it, the API binds to localhost for safety.

Use `--network host` when running this container because **BACnet/IP relies on UDP broadcast and direct interface binding**, which Docker’s default bridged/NAT networking breaks. Host networking allows the container to behave like a real BACnet device on the LAN so discovery (Who-Is / I-Am) works correctly.

Use `--address <ip>/<cidr>[:port]` to explicitly bind BACnet/IP traffic to the **correct NIC** on multi-NIC edge devices (for example, BAS/BMS LAN vs internet). This ensures broadcasts originate on the control network and not the IT network. If the port is omitted, the server defaults to **47808**.

Use `-d` (Detached mode) instead of `-it` to run the container in the background. This allows the BACnet server to operate as a silent daemon service that **does not take over your terminal window**, freeing up your shell for other tasks while the server runs.

Remove `--rm` so the container persists after stopping. Keeping the container allows you to **inspect logs after a crash or restart the same instance later**, whereas `--rm` would immediately delete the container and its history the moment it exits.

Remove `-it` because background services do not require an interactive terminal. Since no user is physically typing into the container console, allocating a pseudo-TTY is unnecessary for a long-running automation service.

Use `--restart unless-stopped` to ensure reliability. This tells Docker to **automatically restart the container** if the application crashes or if the host device reboots, ensuring your BACnet server comes back online without manual intervention.

---

## BACnet client features

The server can act as a **BACnet client** to other devices on the network. These JSON-RPC methods let you discover devices, read/write points, and inspect overrides. Each method is one HTTP POST; some trigger multiple BACnet transactions under the hood.

* **`client_whois_range`** — Who-Is over the given instance range. **Returns:** list of devices (I-Am responses: address, description, vendor, etc.). **Under the hood:** one Who-Is broadcast; one Read Property (description) per device that responds.

* **`client_whois_router_to_network`** — Who-Is-Router-To-Network. **Returns:** list of routers and their networks. **Under the hood:** one broadcast; responses list which networks each router can reach.

* **`client_read_property`** — Read a single property on one object (e.g. `present-value`, `priority-array`). **Returns:** `{ "<property_identifier>": <encoded value> }` (e.g. `{"priority-array": [{"null": []}, ..., {"real": 55}]}`). **Under the hood:** one Read Property. Returns 400 with a clear message if the property is unsupported (e.g. `priority-array` on an analog-input).

* **`client_write_property`** — Write a value to a property, optionally at a given priority (for commandable points). **Returns:** `{ "status": "success", "response": "..." }`. **Under the hood:** one Write Property. Use priority and `"null"` to release an override.

* **`client_read_multiple`** — Read multiple (object, property) pairs in one call. **Returns:** `{ "success": true, "data": { "results": [ ... ] } }`; each result has `object_identifier`, `property_identifier`, `property_array_index`, and `value` (JSON-encodable, including priority-array as list of `{"null": []}` / `{"real": 55}` etc.). **Under the hood:** one or more Read-Property-Multiple (RPM) requests, chunked to stay under APDU size; objects that don’t support a requested property get an error in that result only (rest still returned).

* **`client_point_discovery`** — Discover all points on a device (objects, names, which are commandable). **Returns:** `device_address`, `device_instance`, and `objects`: list of `{ "object_identifier", "name", "commandable" }`. **Under the hood:** Who-Is (device); Read Property `object-list`; then one Read Property `object-name` per object and one Read Property `priority-array` per object (success ⇒ commandable, error ⇒ not). Device object is excluded from the list.

* **`client_supervisory_logic_checks`** — Summary of a device’s commandable points and any active overrides. **Returns:** `device_id`, `address`, `points` (flat list of every override slot: priority level, object, name, type, value), `points_with_overrides` (per-point list with `override_priority_levels`, `has_multiple_overrides`, and `overrides`), and `summary` (`total_points`, `with_priority_array`, `without_priority_array`, `points_with_override_count`). **Under the hood:** runs point discovery (Who-Is, object-list, then one read per point for name and one for priority-array to determine commandable); then one RPM for priority-array on all commandable points; override slots are parsed from the encoded array (e.g. `{"real": 55}` at index 13 ⇒ priority 14).

* **`client_read_point_priority_array`** — Read the full priority array for a single commandable point. **Returns:** list of `{ "priority_level", "type", "value" }` for all 16 slots (null or a value). **Under the hood:** one Read Property `priority-array` on that object.

* **`client_discovery_to_rdf`** — Who-Is over a range, then for each device read object-list and key properties; build an RDF graph and return TTL + summary. **Returns:** `{ "ttl": "...", "summary": { "devices", "objects" } }`. **Under the hood:** one Who-Is; then per device: object-list, then multiple reads for names/properties (can be slow for large ranges).

* **`client_discovery_to_rdf_device`** — Same as above for a single device instance. **Returns:** same shape. **Under the hood:** Who-Is for that instance; then object-list and property reads for that device only.

---

## 🔄 Running Updates and Unit Tests Workflow

Use this workflow when you have pulled new code and need to verify it before redeploying.

### 1. Stop the Running Server
Free up the container name and ports:

```bash
docker stop bens-bacnet
docker rm bens-bacnet

```

### 2. Pull Updates & Run Tests

Stop the docker container and ensure your local Python environment is up to date and that the new code passes all tests.

```bash
# Get latest code
git pull

# Create/Activate Virtual Environment (if not already done)
python3 -m venv env
source env/bin/activate

# Install latest dependencies
pip install -r requirements.txt

# Run the test suite
pytest

```

### 3. Rebuild & Restart (Production)

If tests pass, rebuild the Docker image and launch the long-term server.

**Note:** We add `--env PYTHONPATH=/app` to ensure Python finds the internal modules correctly.

```bash
# 1. Go to BACnet server repo
cd ~/diy-bacnet-server

# 2. Get latest code
git pull

# 3. Stop and remove old container (if running)
docker stop bens-bacnet || true
docker rm   bens-bacnet || true

# 4. Rebuild image
docker build -t diy-bacnet-server .

# 5. Start "production" container again
docker run -d \
  --restart unless-stopped \
  --network host \
  --name bens-bacnet \
  diy-bacnet-server \
  python3 -m bacpypes_server.main \
    --name BensServer \
    --instance 123456 \
    --debug \
    --public


```

### 4. Verify Logs

```bash
docker logs -f bens-bacnet

```

---

## 🧹 Docker Maintenance

**Routine Cleanup**
Removes stopped containers, unused networks, and dangling images:

```bash
docker system prune -f

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

### RDF discovery (BRICK / Open-FDD)

The method **`client_discovery_to_rdf`** runs a deep scan (Who-Is + object-list + key properties), builds an RDF graph with bacpypes3’s `BACnetGraph`, and returns a **TTL** string plus summary. For integration with Open-FDD and BRICK, so BACnet topology can be merged into a single semantic model. Requires `rdflib` (`pip install rdflib`). See Open-FDD’s `docs/bacnet-rdf-and-brick.md` for architecture and merge strategy.

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

## Unit Tests Notes

This test suite ensures that the DIY BACnet Server works reliably as a real, usable application rather than just code that runs. It verifies that the Docker-based BACnet server container starts correctly, initializes its services, and responds as expected. It also confirms that the JSON-RPC interface is correctly wired, exposing the appropriate RPC entrypoint and methods, and that important RPC helpers—such as the server readiness check and BACnet Who-Is discovery wrapper—can execute safely without crashing. Together, these tests validate the integration between FastAPI, fastapi-jsonrpc, Pydantic models, and BACpypes3 to ensure the system behaves as a functional BACnet utility service.


```bash
# run tests from a virtual environment
python3 -m venv env
. ./env/bin/activate
pip install -r ./requirements.txt

pytest tests/ -v
```

---


## 📜 License

Everything here is **MIT Licensed** — free, open source, and made for the BAS community.  
Use it, remix it, or improve it — just share it forward so others can benefit too. 🥰🌍


【MIT License】

Copyright 2025 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.