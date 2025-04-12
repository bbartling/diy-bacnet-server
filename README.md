## 🚀 diy-bacnet-server (Now with JSON-RPC)

A lightweight, containerized **BACnet/IP server** powered by **FastAPI + JSON-RPC**, designed for rapid development, prototyping, and integration within modern microservice environments.

The app reads a **CSV configuration file** at startup to define BACnet points and provides a **JSON-RPC API** (instead of REST) for interacting with the BACnet/IP server.

> **NEW:** JSON-RPC compliant interface with built-in [OpenRPC](https://spec.open-rpc.org/) schema support and Swagger-compatible `/docs` endpoint based on the [fastapi-jsonrpc](https://github.com/smagafurov/fastapi-jsonrpc) library.

---

## 📂 CSV Configuration Format

Place a CSV file in the `csv_file` directory with the following format. It is parsed at startup to define the exposed BACnet points:

```csv
Name,PointType,Units,Commandable
chillerEnable,BV,Status,Y
chwSetPoint,AV,degrees celsius,Y
chillerDemandLimit,AV,,N
evapDP,AV,kpa pressure units,N
evapFlow,AV,,N
```

### Columns:
- **Name**: Required. BACnet `objectName`.
- **PointType**: Required. Only `AV` (Analog Value) or `BV` (Binary Value) supported.
- **Units**: Optional. BACnet `EngineeringUnits` (defaults to `noUnits` if omitted).
- **Commandable**: `Y` for writable priority-array points, `N` for read-only.

---

## 🔧 API Access (via JSON-RPC)

The server starts at:
```
http://localhost:8080/
```
Interactive Swagger docs:
```
http://localhost:8080/docs
```

All **RPC methods** are sent as `POST /` with a JSON-RPC 2.0 body.

### Example Request Body:
```json
{
  "jsonrpc": "2.0",
  "method": "client_read_property",
  "params": {
    "device_instance": 123456,
    "object_identifier": "analog-output,1",
    "property_identifier": "present-value"
  },
  "id": "0"
}
```

### Example Response:
```json
{
  "jsonrpc": "2.0",
  "result": {
    "chwSetPoint": 0.0
  },
  "id": "0"
}
```

### Fields:
- `jsonrpc`: Always `"2.0"` (protocol version).
- `result`: The return value.
- `id`: Echoes the request ID for correlation.

---

## 🛠️ Supported RPC Methods


### ✅ `server_hello`  
> Returns a welcome message.

### ✅ `server_update_points`  
> Updates values via a dictionary payload for the BACnet server. Discoverable BACnet server objects (sometimes called "points") are defined in the CSV configuration file.

### ✅ `server_read_commandable`  
> Reads only commandable BACnet server point values. These are points that can be written to by an external control system, such as a BAS. This method retrieves the latest values that were written to the server over BACnet for commandable points defined in the CSV file.

### ✅ `server_read_all_values`  
> Reads the present values of all BACnet server points defined in the configuration, regardless of whether they are writable or read-only.

### ✅ `client_read_property`  
> A BACnet client feature used to read any BACnet property from a discovered remote device.

### ✅ `client_write_property`  
> A BACnet client feature used to write a value to a BACnet property on a remote device.

### ✅ `client_read_multiple`  
> A BACnet client feature that uses the ReadPropertyMultiple (RPM) service to fetch multiple properties from a single remote BACnet device in one request.

### ✅ `client_whois_range`  
> Sends a `Who-Is` broadcast across a specified range of BACnet device instance IDs to discover devices on the network.


### ⏳ Planned Future RPC Methods

- [ ] `point_discovery`  
- [ ] `supervisory_logic_checks`  
- [ ] `read_point_priority_arr`  
- [ ] `whohas`  
- [ ] `who_is_router_to_network`  


---

## 🔗 Runtime JSON Device Configuration
Place this config in a JSON file for identifying the device during BACnet discovery:

```json
{
  "device_name": "BensBACnetServer",
  "device_instance": 1234567
}
```

---


### 🐳 1. Install Docker & docker-compose on Raspberry Pi

**Note** - The commands below were tested on an older raspberry pi 3 model which used legacy docker compose with commands that have dashes such as a `docker-compose up --build -d`. Newer Pis or versions of docker compose you need to run commands without the dash such as a `docker compose up --build -d`.

```bash
# Install Docker
curl -sSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

Then **log out and back in**, or run:
```bash
newgrp docker
```

To install docker-compose plugin:
```bash
sudo apt install docker-compose-plugin
```

Verify:
```bash
docker-compose version
```

---

### ⚙️ 2. Build & Run Using docker-compose

From the project root where `docker-compose.yml` is located:

```bash
docker-compose up --build -d
```

---

### 📋 3. View Logs

All services:
```bash
docker-compose logs -f
```

Just BACnet server:
```bash
docker-compose logs -f bacnet_server
```

---

### 🧹 4. Stop and Clean Up
* note: `-d` stands for detached mode, which means “Run the containers in the background.”

```bash
docker-compose build && docker-compose up -d --remove-orphans
```
---

### 🔁 5. Rebuild Completely (Clean Start)
* note: `-d` stands for detached mode, which means “Run the containers in the background.”
```bash
docker-compose build --no-cache && docker-compose up -d --remove-orphans
```

---

## 🔄 Common Docker Commands

### List all containers:
```bash
docker ps -a
```

### Stop and remove all containers:
```bash
docker stop $(docker ps -aq)
docker rm $(docker ps -aq)
```

### Full cleanup (⚠️ removes everything):
```bash
docker system prune -a --volumes
```

---

## ✅ Troubleshooting

### Access Docker shell:
```bash
docker exec -it bacnet_server bash
```

### Test BACnet communication from other free 3rd party tools:
Use `bacnet-read` or `bacnet-write` from tools like Yabe or the BACnet Discovery Tool (BDT)

---


## 📜 License
`diy-bacnet-server` is released under the **MIT License**, ensuring it remains free and accessible for all.

---

【MIT License】

Copyright 2025 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.