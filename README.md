## diy-bacnet-server

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2.svg?logo=discord&logoColor=white)](https://discord.gg/Ta48yQF8fC)
[![CI](https://github.com/bbartling/diy-bacnet-server/actions/workflows/ci.yml/badge.svg)](https://github.com/bbartling/diy-bacnet-server/actions/workflows/ci.yml)
![MIT License](https://img.shields.io/badge/license-MIT-green.svg)
![Development Status](https://img.shields.io/badge/status-Beta-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)

Lightweight BACnet/IP + JSON-RPC edge microservice for Docker-based deployments, including optional Modbus TCP client features.


## Quick Start

This is a mini tutorial for bacpypes3 which is super useful for troubleshooting purpoeses. See further below for setup with the full-featured DIY BACnet server, which includes a web app powered by FastAPI and supports easy Docker deployments.


---

## Quick Test (Raw bacpypes3)

Set up a minimal Python environment and run a basic bacpypes3 instance:

```bash
# Create virtual environment
python -m venv env

# Activate (Linux / macOS)
. env/bin/activate

# Install dependencies
pip install bacpypes3 ifaddr
```

### Run bacpypes3 Test Instance

```bash
python -m bacpypes3 \
  --name BensRawBacpypes3Test \
  --address 192.168.204.12/24 \
  --instance 123456 \
  --debug
```

This will start a basic BACnet device on your network for testing discovery (`whois`) and communication.


```bash
> help
commands: config, exit, help, iam, ihave, irt, rbdt, read, rfdt, rpm, wbdt, whohas, whois, wirtn, write
```

#### Example: Device Discovery (`whois`)

```bash
> whois
```

Example output (trimmed):

```
3456788 192.168.204.16
3456789 192.168.204.13
3456790 192.168.204.14
```

#### Common Commands

```bash
# Discover devices in a range
whois 1000 3456799

# Read a point
read 192.168.204.13 analog-input,1 present-value

# Write a value (priority 9)
write 192.168.204.14 analog-output,1 present-value 999.8 9

# Release a command (null write)
write 192.168.204.14 analog-output,1 present-value null 9
```

---

## Server Flags

The app supports the same flags as bacpypes3:

* `--name` → Device name
* `--instance` → Device instance ID
* `--address` → IP/subnet/port (optional)
* `--public` → Enable LAN HTTP access + `/docs`

> Tip: Omit `--address` when a single NIC is sufficient.

---

## Python (Local Setup)

This example sets up the server locally and generates a Bearer token via a `.env` file.

```bash
git clone https://github.com/bbartling/diy-bacnet-server.git
cd diy-bacnet-server

python3 -m venv .venv
. .venv/bin/activate

pip install -e ".[dev]"

# Create API key
printf 'BACNET_RPC_API_KEY=%s\n' "$(openssl rand -hex 32)" > .env

# Load environment variables
set -a && . ./.env && set +a

# Run server
python -m bacpypes_server.main \
  --name my-device \
  --instance 123456 \
  --address 192.168.204.18/24:47808 \
  --public \
  --debug
```

---

## Accessing the API

With `--public` enabled:

* Open API docs:

  ```
  http://127.0.0.1:8080/docs
  ```

  (or use the host’s LAN IP from another machine)

### Authentication

* `POST /server_hello` → No auth required
* All other JSON-RPC endpoints → Require Bearer token (if API key is set)

---

## Notes

* Ensure UDP port **47808** is open for BACnet discovery (Who-Is / I-Am).
* The `.env` file is optional for local, unsecured loopback testing.
* Behavior should match standard bacpypes3 discovery and communication patterns.

### Common Gotcha: Firewall (Same Story as BACnet)

The most common issue is firewall configuration.

You may already have UDP `47808` open for BACnet, but the HTTP API (JSON-RPC / Swagger) runs on **TCP 8080**. This can cause a confusing situation where:

* `curl` or browser **works locally on the server**
* but **fails from another machine on the LAN**

#### Fix (UFW examples)

Allow port 8080:

```bash
sudo ufw allow in on enp3s0 to any port 8080 proto tcp comment 'diy-bacnet HTTP'
```

Or more broadly:

```bash
sudo ufw allow 8080/tcp
```

Verify:

```bash
sudo ufw status numbered
```

#### Test from another machine on the LAN

```bash
curl -sS -o /dev/null -w '%{http_code}\n' http://192.168.204.18:8080/docs
```

Expected result:

```
200
```

If you don’t see `200`, it’s almost always a firewall or network interface binding issue.

---

### Docker

`--network host` is a Docker option: the container shares the host’s network stack instead of a private bridge/NAT network. That keeps BACnet/IP (UDP broadcasts and port 47808) behaving like running Python directly on the machine. Swagger **Authorize** still uses the same `BACNET_RPC_API_KEY` value you put in `.env`. Skip `git clone` / `cd` if you already have the repo.

```bash
git clone https://github.com/bbartling/diy-bacnet-server.git
cd diy-bacnet-server
printf 'BACNET_RPC_API_KEY=%s\n' "$(openssl rand -hex 32)" > .env
docker build -t diy-bacnet-server .
docker run --rm -it --network host --env-file .env --name diy-bacnet-gateway diy-bacnet-server \
  python3 -u -m bacpypes_server.main \
  --name asdf --instance 123456 --address 192.168.204.18/24:47808 --public --debug
```

Swagger **Authorize** uses the same `BACNET_RPC_API_KEY` value as in that file.

## Online documentation

- [bbartling.github.io/diy-bacnet-server](https://bbartling.github.io/diy-bacnet-server/)

## Dependancies

- Python 3.12+ (for local runs and tests)
- `pip` + virtual environment tooling (`python3 -m venv`)
- Docker (for container runs); use `--network host` for BACnet/IP behavior
- OpenSSL (optional, used in examples to generate `BACNET_RPC_API_KEY`)
## License

MIT. See `LICENSE`.
