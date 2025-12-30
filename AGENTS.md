# AGENTS.md — DIY Edge Lambda Context

## 1. Project Identity & Scope
Role: Building Automation Systems (BAS) Developer & IoT Architect.
Platform: "DIY Edge Lambda" — A local-first, docker-friendly ecosystem for smart building automation.
Distinction: While this mimics AWS Lambda's structure (handlers, zips), it runs locally on Linux edge devices (Raspberry Pi, etc.).
Core Constraint: Do NOT use cloud libraries (AWS SDK/Boto3) unless explicitly requested. All hardware interaction happens via local HTTP JSON-RPC calls.

---

## 2. The "Edge Triad" Architecture

### A. Component Roles
1.  DIY BACnet Server (The I/O Layer)
    * Role: Speaks native BACnet/IP to physical equipment. Exposes a JSON-RPC 2.0 API via HTTP.
    * Human Interface: Swagger UI (`/docs`). Engineers use this to discover points and test writes manually.
    * Agent Interface: HTTP POST requests. Agents act as HTTP clients sending JSON-RPC envelopes.

2.  DIY Edge Lambda Manager (The Runtime)
    * Role: Manages the lifecycle (start/stop/log) of the agent processes.
    * Port: 8000 (standard).

3.  DIY Edge Lambda Agents (The Logic)
    * Role: Python `subprocess` workloads.
    * Constraint: Stateless logic loops. They read from the Server, calculate, and write back to the Server.

---

## 3. API & Data Access (JSON-RPC Protocol)

CRITICAL IMPLEMENTATION DETAIL:
Agents interact with the BACnet Server exclusively via JSON-RPC 2.0 over HTTP POST.
The server exposes specific endpoints for each method (e.g., `/client_read_multiple`) to keep the API clean and discoverable via Swagger.

### A. The Request Envelope
Every request from an agent must act as a JSON-RPC client.
* Method: `POST`
* Headers: `Content-Type: application/json`
* Body Structure:
    ```json
    {
      "jsonrpc": "2.0",
      "id": "0",
      "method": "<METHOD_NAME>",
      "params": {
         "request": { <ACTUAL_DATA_HERE> }
      }
    }
    ```

### B. Core Methods (The "Standard Library")
*Reference these methods when writing agent logic:*

#### 1. `client_read_multiple` (RPM)
* Use for: Bulk telemetry (Sensors, Feedback).
* Endpoint: `/client_read_multiple`
* Params: `{"device_instance": int, "requests": [{"object_identifier": "analog-input,1", "property_identifier": "present-value"}, ...]}`

#### 2. `client_write_property` (Commanding)
* Use for: Changing setpoints or actuator positions.
* Endpoint: `/client_write_property`
* Params:
    * `value`: The target value (number) or `"null"` (string) to release.
    * `priority`: Required. 16 (sched), 12 (routine), 8 (safety).
    * `property_identifier`: usually `"present-value"`.

#### 3. `client_read_point_priority_array` (Arbitration)
* Use for: Checking if a point is already overridden (Crucial for "Dueling Agents" and safe optimization).
* Endpoint: `/client_read_point_priority_array`
* Returns: A sparse array (dict) of current priorities (e.g., `{"16": 72.0, "8": "null"}`).

#### 4. `client_whois_range` & `client_point_discovery`
* Use for: Network scanning and auto-configuration agents.

---

## 3. Implementation Rules

### A. Directory Structure
Every agent must follow this exact layout:
```text
agents/
  {agent_name}/
    ├── lambda_function.py    # The entry point
    ├── config.json           # Configuration (IPs, Device IDs)
    ├── requirements.txt      # Dependencies (keep light, usually just `requests`)
    └── config.json.example   # Template for users

```

### B. The "Lambda" Pattern

Even though we run forever, we respect the handler signature for compatibility.

```python
# Standard Pattern
import time
import requests

def loop_forever():
    cfg = load_config()
    while True:
        # 1. Read Inputs (JSON-RPC)
        # 2. Compute Logic
        # 3. Write Outputs (JSON-RPC)
        time.sleep(cfg['interval'])

def handler(event=None, context=None):
    """Entry point required by the Manager."""
    loop_forever()

```

### C. Data Access (JSON-RPC)

Never try to import `bacpypes3` directly in the agent. ALWAYS use `requests` to hit the BACnet Server.

* Read Multiple (RPM):
* Method: `client_read_multiple`
* Use for bulk fetching telemetry (Temps, Setpoints).


* Write with Priority:
* Method: `client_write_property`
* *Rule:* Always specify a priority level (usually 12-16 for auto, 8 for safety).
* *Release:* To release an override, write value `"null"` (string).



---

## 4. The "Dueling Agents" Testing Protocol

*Use this pattern when asked to validate system stability or test race conditions.*

Concept: Two identical agents running in parallel that fight over a single setpoint.
Goal: Verify the `priority-array` logic and `read/write` stability without crashing the server.

### The Logic Flow (The "Duel")

1. Target: A VAV Box (Zone Cooling Setpoint).
2. Action A (Check): Read `priority-array` at level 12.
3. Action B (Duel):
* IF Priority 12 is *Occupied* (not null) -> WRITE "null" (Release).
* IF Priority 12 is *Empty* (null) -> WRITE 70.0 (Claim).


4. Result: The setpoint constantly flips between `70.0` and `Default`.
5. Telemetry: Simultaneously perform a `READ_MULTIPLE` on an AHU to generate background traffic load.

---

## 5. Development Workflow (Mental Sandbox)

### Packaging

* Do not hallucinate complex build pipelines.
* Use the provided `pack_agent.py` script.
* Command: `python pack_agent.py {agent_name}` -> outputs `dist/{agent_name}.zip`.

### Configuration

* Hardcoding IPs is forbidden.
* Always load `bacnet_base_url` from `config.json` or env var `BACNET_BASE_URL`.

### Safety Rails

* Fail-Safe: Wrap the main loop in a `try/except` block. If a read fails, log it and `continue`. Do not let the process crash/exit.
* Logging: Use standard `print()` or `logging`. The Manager captures stdout/stderr.

---

## 6. Glossary

* RPM: Read Property Multiple (High efficiency reading).
* COV: Change of Value (Avoid polling if possible, but polling is standard for these agents).
* Priority 12: Standard "Normal Operation" override slot.
* Priority 8: "Manual/Safety" override slot (High priority).
* Null: The specific JSON value sent to "release" a BACnet override.

