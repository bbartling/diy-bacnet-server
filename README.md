## 🚀 diy-bacnet-server

A lightweight, containerized **BACnet/IP server** powered by **FastAPI**, designed for rapid development, prototyping, and integration within modern microservice environments. This app reads a **CSV configuration file** at startup to define BACnet points and provides a **REST API** for updating and retrieving values.

By default, it binds to **localhost**, making it safe for development and ideal for pairing with other Docker apps. It has been tested with over **300 BACnet points**, supporting **`POST /update` updates and `GET /read` reads every 4 seconds** without performance issues. The `POST /update` updates the BACnet server app point present values and the `GET /read` retrieves data being written to the BACnet server via BACnet/IP.

---

## 🧾 CSV Configuration Format

Simply place a CSV file in the `csv_file` directory with the following structure. It is parsed at application startup to define the BACnet points exposed by the server. The app only supports BACnet Analog Values (AV) or Binary Values (BV) both of which can be configured as writeble or commandable.

```csv
Name,PointType,Units,Commandable
chillerEnable,BV,Status,Y
chwSetPoint,AV,degrees celsius,Y
chillerDemandLimit,AV,,N
evapDP,AV,kpa pressure units,N
evapFlow,AV,,N
```

### Column Descriptions:

- **Name**: Required. The `objectName` used in BACnet for each point.
- **PointType**: Required. Currently BACnet Analog Values or Bindary Value objects are supported; input an `AV` or `BV` value only.
- **Units**: Optional. Matches BACnet `EngineeringUnits`; defaults to `noUnits` if blank.
- **Commandable**: Use `Y` for writeable points (`AV`/`BV` with priority array support), or `N` for read-only.

---

## ⚙️ Example Use Cases

- For embedded Linux projects make a BACnet server for your chiller or AHU or anything really.
- For IoT edge use Node-RED or other IoT automation tools that do not have BACnet server support. This app will allow for a BAS to interact with the server via BACnet/IP.
- Simulate field devices in a containerized environment.

---

## 🔧 Set JSON Config File
Use a text editor to input this data for your BACnet server device name and instance ID. This will show up when some 3rd party control system like a building automation system (BAS) discovers the app from a BACnet `Who-Is` request the app will respond with this data in the form of a BACnet `I-Am` using the underlying Python BACnet stack.

```json
{
    "device_name": "BensBACnetServer",
    "device_instance": 1234567
}
```

---

## 🔌 API Usage
The app exposes a simple REST API using **FastAPI**, available by default at:

```
http://localhost:8080
```

You can visit the interactive API docs at but note that Swagger UI is not visible from the outside as the app is hardcoded for `host="127.0.0.1", port=8080, log_level="info"` for security reasons:

```
http://localhost:8080/docs
```

### 📥 `POST /update`

**Update BACnet point values** via JSON.

#### Example Request:

```json
POST /update
Content-Type: application/json

{
  "SupplyTempSetPoint": 55.2,
  "ChillerEnable": true
}
```

- Values are type-checked: analog points accept floats, binary points accept booleans or `"active"` / `"inactive"`.
- Only **commandable points** are writable.
- Response includes only changed or error values.

---

### 📤 `GET /read`

**Retrieve all current values** of **commandable points**.

#### Example Response:

```json
{
  "SupplyTempSetPoint": 55.2,
  "ChillerEnable": "active"
}
```

- Includes only points marked `Commandable = Y` in the CSV.
- Analog values returned as floats.
- Binary values returned as `"active"` or `"inactive"`.

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