## diy-bacnet-server

A lightweight Docker container app that spins up a BACnet/IP server using a simple **CSV file as configuration**, with full **read/write REST API support**.

It runs using **FastAPI** and is intended to be **hosted on localhost by default**, designed to act as a drop-in BACnet server in a broader microservice architecture — ideal for testing, prototyping, and integration with other Docker-based systems.

---

## 🧾 CSV Config File Format Expectations

Your configuration CSV should follow this format:

```csv
Name,Data Address,Units,Commandable
SupplyTempSetpoint,1,degreesFahrenheit,Y
ReturnTemp,2,degreesFahrenheit,N
StatusFlag,3,,Y
```

### 🔑 CSV Config File Columns Explained

- **`Name`**: (Required) Used as the `objectName` in BACnet. This is how you reference the point in API requests.
- **`Data Address`**: (Optional) Can be used for internal reference, included in the object's description.
- **`Units`**: (Optional) Engineering units like `degreesFahrenheit`, `percent`, etc. Defaults to `noUnits` if left blank.
- **`Commandable`**: (Required) Use `Y` to make the point **BACnet writable** using a priority array (i.e., a `Commandable` object). Use `N` for read-only.

---

## ⚙️ Example Use Cases

- For embedded Linux projects make a BACnet server for your chiller or AHU or anything really.
- Connect to Node-RED or other IoT automation tools that interact with BACnet/IP in edge environments.
- Simulate field devices in a containerized environment.

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

### Access Node-RED shell:
```bash
docker exec -it nodered bash
```

### Test BACnet communication from Node-RED:
Use `bacnet-read` or `bacnet-write` nodes to talk to `bacnet_server`.

### Verify `bacnet_server` is responding:
From a BACnet tool (e.g., YABE or VTS), scan for devices via UDP at the host IP on port 47808.

---


## 📜 License
`diy-bacnet-server` is released under the **MIT License**, ensuring it remains free and accessible for all.

---

【MIT License】

Copyright 2025 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.