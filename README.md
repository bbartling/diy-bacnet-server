## 🚀 diy-bacnet-server (Now with JSON-RPC)

A lightweight, containerized **BACnet/IP server**, built as a fully asynchronous **asyncio**-based application using **bacpypes3**, **FastAPI**, and **JSON-RPC**. It's designed for rapid development, prototyping, and seamless integration into modern microservice environments via Docker—ideal for IoT edge deployments.

The app reads a **CSV configuration file** at startup to define BACnet points and provides a **JSON-RPC API** (instead of REST) for interacting with the BACnet/IP server.

> JSON-RPC compliant interface with built-in [OpenRPC](https://spec.open-rpc.org/) schema support and Swagger-compatible `/docs` endpoint based on the [fastapi-jsonrpc](https://github.com/smagafurov/fastapi-jsonrpc) library.

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

Here’s a concise but clear section you can drop into your `README.md` to explain using VS Code’s tunnel feature for viewing the Swagger UI securely:

---

### 🔒 Accessing the Swagger UI via VS Code Tunnel

For **security reasons**, the BACnet RPC API is hardcoded to run on `localhost` (127.0.0.1), meaning it is **not accessible externally** by default. However, when developing remotely (e.g., via SSH into a Linux server or Raspberry Pi), you can still **view the Swagger UI and test endpoints securely** using **VS Code's built-in SSH tunneling**.

#### ✅ Steps to Use the Tunnel Feature:

1. **Connect to the remote host using VS Code Remote - SSH.**

2. Run the app:
   ```bash
   python3 main.py --name BensServer --instance 123456
   ```

3. When the app starts, it will log:
   ```
   JSON-RPC API ready at http://localhost:8080/docs
   ```

4. **VS Code will prompt you** to forward port `8080`. Click **"Forward Port"** when prompted.

5. Open your browser on your local machine and go to:
   ```
   http://localhost:8080/docs
   ```

   You’ll now see the full **Swagger UI** for the JSON-RPC API.


![Swagger UI](https://github.com/bbartling/diy-bacnet-server/blob/develop/snip.png)


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

---

### ✅ `server_update_points`  
> Updates values via a dictionary payload for the BACnet server.  
Discoverable BACnet server objects (sometimes called "points") are defined in the CSV configuration file.

---

### ✅ `server_read_commandable`  
> Reads only *commandable* BACnet server point values.  
These are points that can be written to by an external control system, such as a BAS. This method retrieves the latest values that were written to the server over BACnet for commandable points defined in the CSV file.

---

### ✅ `server_read_all_values`  
> Reads the present values of **all** BACnet server points defined in the configuration, regardless of whether they are writable or read-only.

---

### ✅ `client_read_property`  
> A BACnet client feature used to read any BACnet property from a discovered remote device.  
Supports single-property reads using object identifier and property name.

---

### ✅ `client_write_property`  
> A BACnet client feature used to write a value to a BACnet property on a remote device.  
Supports priority-based override logic if a priority level is specified.

---

### ✅ `client_read_multiple`  
> A BACnet client feature that uses the **ReadPropertyMultiple (RPM)** service to fetch multiple properties from a single remote BACnet device in one request.

---

### ✅ `client_whois_range`  
> Sends a **Who-Is** broadcast across a specified range of BACnet device instance IDs to discover devices on the network.  
Returns all I-Am responses along with metadata like vendor ID and description.

---

### ✅ `client_point_discovery`  
> For a given `device_instance`, performs a discovery of all objects and their human-readable names.  
Useful for populating a list of points available for polling, command, or analytics.

---

### ✅ `client_supervisory_logic_checks`  
> Scans all objects for a single device, identifies those that support the **priority-array** property, and returns the active override values (if any).  
This simulates supervisory control logic that checks if a point is under manual or automatic control.

---

### ✅ `client_read_point_priority_array`  
> Reads the full priority array (1–16 levels) for a single point.  
Returns a list of priority levels and their current values including nulls. This is useful for understanding overrides in effect on a writable BACnet object.

---

### ⏳ Planned Future RPC Methods


- [ ] `whohas` - to search for points on a BACnet system by a point name.
- [ ] `who_is_router_to_network` - to discover BACnet MSTP networks inside a building.


---
### ⚡ Test App 

```bash
python3 bacpypes_server/main.py --name BensServer --instance 123456 --debug
```
---
#### 🐳 **Like Docker?**  
If you'd rather run this in a container, check out the **[Docker Setup Guide](https://github.com/bbartling/diy-bacnet-server/blob/develop/docker_readme.md)**. 🚀

---

## 📜 License
`diy-bacnet-server` is released under the **MIT License**, ensuring it remains free and accessible for all.
---

【MIT License】

Copyright 2025 Ben Bartling

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.