# MQTT + diy-bacnet-server — Home Assistant, Open-FDD, and optional RPC gateway

This guide covers three related ideas:

1. **Home Assistant + BACnet2MQTT** — point state and HA discovery (browser-friendly steps below).
2. **Open-FDD–hosted Mosquitto** — when you run **[Open-FDD](https://github.com/bbartling/open-fdd)** with `./scripts/bootstrap.sh --with-mqtt-bridge`, the stack can start a **local broker** (`localhost:1883`) so **diy-bacnet-server** (and other services) use a **generic** MQTT broker—no cloud vendor required.
3. **MQTT RPC gateway (experimental)** — a separate feature in **diy-bacnet-server**: subscribe on `{prefix}/cmd`, publish acks on `{prefix}/ack`, optional telemetry topics. Same JSON-RPC **method** names as HTTP; intended for future Open-FDD / automation integration. See the **[README — MQTT RPC gateway](README.md#mqtt-rpc-gateway-optional-experimental)** for env vars, topics, and `mosquitto_pub` examples.

**Relationship:** BACnet2MQTT is for **per-point** topics and Home Assistant discovery. The MQTT RPC gateway is for **request/response-style** commands over pub/sub (Who-Is, read property, server point updates, etc.). You can run one, both, or neither; each is gated by its own env flags.

---

## Home Assistant + BACnet2MQTT — Try-it-yourself cheat sheet

Get your DIY BACnet server’s points into Home Assistant over MQTT (browser-only, beginner-style). Same idea as **Zigbee2MQTT**: one broker, discovery, entities in HA.

### 1. Prerequisites

- **diy-bacnet-server** running (Docker or local) with a CSV that defines your points.
- **Home Assistant** running (e.g. on the same host or another machine that can reach the broker).
- An **MQTT broker** that both the BACnet server and Home Assistant can use (e.g. Mosquitto on the HA host, **or** Mosquitto started by **Open-FDD** with `--with-mqtt-bridge` if HA and the gateway share that network).

### Open-FDD broker tip

If the BACnet container uses **`--network host`** (Open-FDD default for **diy-bacnet-server**), `MQTT_BROKER_URL=mqtt://127.0.0.1:1883` targets Mosquitto on the **same host** as the gateway. Point Home Assistant’s MQTT integration at that host if HA also runs there, or use the LAN IP if HA is elsewhere.

---

### 2. Install / configure the MQTT broker (in Home Assistant)

1. In HA: **Settings → Add-ons** (or **Settings → Devices & services → Add-ons**).
2. If you don’t have **Mosquitto broker**: install **“Mosquitto broker”** from the add-on store.
3. Open the add-on → **Configuration** (leave defaults or set a log level).
4. **Start** the add-on. Note the port (default **1883**).
5. In the add-on’s **Log** tab, confirm it says the broker is listening.

If you prefer a **manual** (non-add-on) broker on the same host as HA, install Mosquitto there, start it, and use that host/port in the steps below.

---

### 3. Add the MQTT integration in Home Assistant

1. **Settings → Devices & services → Add integration**.
2. Search for **“MQTT”**.
3. Add **MQTT**.
4. In the MQTT config:
   - **Broker**: `localhost` if the broker is on the same machine as HA; otherwise the IP/hostname of the machine running the broker.
   - **Port**: `1883` (default).
   - **Username / Password**: leave blank unless you configured the broker with auth.
5. **Submit**. You should see “Connected” for the MQTT integration.

---

### 4. Run the BACnet server with the MQTT bridge

Set these **environment variables** so the BACnet server starts the bridge and points to your broker:

| Variable | Example | Meaning |
| -------- | ------- | ------- |
| `BACNET2MQTT_ENABLED` | `true` | Turn on the bridge. |
| `MQTT_BROKER_URL` | `mqtt://192.168.1.10:1883` | Broker URL. Use the HA host IP if the broker is there. |
| `HA_DISCOVERY_ENABLED` | `true` | Publish HA MQTT discovery so entities appear automatically. |
| `HA_DISCOVERY_TOPIC` | `homeassistant` | Discovery topic (default; leave unless you know you need another). |

**Docker example** (broker at 192.168.1.10):

```bash
docker run -d \
  --restart unless-stopped \
  --network host \
  --name bens-bacnet \
  -e BACNET2MQTT_ENABLED=true \
  -e MQTT_BROKER_URL=mqtt://192.168.1.10:1883 \
  -e HA_DISCOVERY_ENABLED=true \
  diy-bacnet-server \
  python3 -m bacpypes_server.main \
    --name BensServer \
    --instance 123456 \
    --debug \
    --public
```

If the broker is on the **same host** as the container, use `mqtt://127.0.0.1:1883` (with `--network host` the container shares the host network).

Restart the BACnet server after changing env vars so the bridge (re)connects and publishes discovery.

---

### 5. Check that the bridge is talking MQTT

1. In HA: **Settings → Devices & services → MQTT → Configure** (or **MQTT** card).
2. Open **Listen to a topic** (or use **Tools → MQTT** if available).
3. Subscribe to:
   - `bacnet2mqtt/#`
4. You should see:
   - `bacnet2mqtt/bridge/state` → `online`
   - `bacnet2mqtt/bridge/info` → JSON (version, BACnet instance)
   - `bacnet2mqtt/bridge/devices` → JSON list of points
   - `bacnet2mqtt/<point_name>` → JSON like `{"present_value": 72.5, "units": "degreesFahrenheit"}`

If you see these, the bridge and broker are good.

---

### 6. See entities in Home Assistant

With **HA_DISCOVERY_ENABLED=true**, the bridge publishes MQTT discovery messages. HA should create entities after a short delay (or after **Settings → Devices & services → MQTT → Reload** if your HA has it).

1. **Settings → Devices & services** → find the **MQTT** integration.
2. You should see a device (e.g. “BACnet” or your bridge name) with entities under it.
3. Or go to **Overview** (dashboard) and check **Entities**; search for your point names (e.g. `outdoor-temp`, `setpoint-temp`, `optimization-enable`).

Entity types you’ll get:

- **Sensors** (read-only): analog inputs (AI), binary inputs (BI), multistate inputs (MSI), read-only values, Schedule.
- **Numbers** (commandable analog): setpoints (AV/AO with Commandable=Y).
- **Switches** (commandable binary): e.g. BV with Commandable=Y.

---

### 7. Control and limits (important)

- **Read-only points** (sensors): HA shows live values from the BACnet server; no control.
- **Commandable points** (setpoints, switches): HA shows state. **Writes from HA to MQTT are currently not applied** to commandable points (the server skips them to avoid conflicting with BACnet priority). Control those via the BACnet API (e.g. JSON-RPC) or a future bridge update.

So: use this setup to **monitor** all points in HA and to **control** only non-commandable points that the server allows to be updated via MQTT (e.g. simulated inputs). For full “Zigbee2MQTT-style” control of setpoints/switches, a later bridge version may add MQTT → commandable writes.

---

### 8. Optional env vars (reference)

| Variable | Default | Description |
| -------- | ------- | ----------- |
| `MQTT_BASE_TOPIC` | `bacnet2mqtt` | Topic prefix for state and commands. |
| `MQTT_POLL_INTERVAL_SEC` | `30` | How often the bridge publishes each point’s state. |
| `MQTT_USER` / `MQTT_PASSWORD` | — | Broker username/password if required. |

---

### 9. Troubleshooting (browser-only)

- **No entities**
  - Confirm `HA_DISCOVERY_ENABLED=true` and the server was restarted.
  - In MQTT Listen, check that topics under `homeassistant/` are published (sensor/number/switch configs).
  - Reload MQTT in HA if available.

- **Bridge not connected**
  - Check `MQTT_BROKER_URL` (host and port). From the BACnet server’s network, can it reach the broker? Use the HA host IP if the broker is there.
  - Check server logs for “BACnet2MQTT bridge” messages (connected vs errors).

- **State not updating**
  - Check `bacnet2mqtt/<point_name>` in MQTT Listen; if it updates every ~30 s, the bridge is publishing. If HA entities don’t update, try reloading the MQTT integration or restarting HA.

- **Broker auth**
  - If the broker has a username/password, set `MQTT_USER` and `MQTT_PASSWORD` and configure the same credentials in **Settings → Devices & services → MQTT**.

---

## Quick checklist

- [ ] MQTT broker installed and running (e.g. Mosquitto add-on in HA, or Open-FDD `--with-mqtt-bridge`).
- [ ] MQTT integration added in HA and connected.
- [ ] BACnet server run with `BACNET2MQTT_ENABLED=true`, `MQTT_BROKER_URL=...`, `HA_DISCOVERY_ENABLED=true`.
- [ ] MQTT Listen shows `bacnet2mqtt/bridge/state` = online and `bacnet2mqtt/<point_name>` messages.
- [ ] Entities appear under MQTT device in HA; sensors show values.
- [ ] Remember: commandable points are read-only from HA for now; use BACnet/API to change them.
- [ ] (Optional future) MQTT RPC gateway: see main **README** and Open-FDD **docs/howto/mqtt_integration.md**.

Done. You’re good to try the integration yourself from the browser.
