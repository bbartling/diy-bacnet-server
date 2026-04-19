## diy-bacnet-server

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2.svg?logo=discord&logoColor=white)](https://discord.gg/Ta48yQF8fC)
[![CI](https://github.com/bbartling/diy-bacnet-server/actions/workflows/ci.yml/badge.svg)](https://github.com/bbartling/diy-bacnet-server/actions/workflows/ci.yml)
![MIT License](https://img.shields.io/badge/license-MIT-green.svg)
![Development Status](https://img.shields.io/badge/status-Beta-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python&logoColor=white)

Lightweight BACnet/IP + JSON-RPC edge microservice for Docker-based deployments, including optional Modbus TCP client features.

## Quick start

Same flags as the bacpypes3 module: `--name`, `--instance`, optional `--address`, and `--public` for LAN HTTP and `/docs`. Drop `--address` when a single NIC is enough.

For **Python (local)** and **Docker**, use the same **`.env` in the repository root** (next to `Dockerfile` / `pyproject.toml`): one `BACNET_RPC_API_KEY=…` line. Local runs load it with `set -a && . ./.env`; Docker passes it with `--env-file .env` from that same directory.

### Python (local)

Create a gitignored `.env` with one line, `BACNET_RPC_API_KEY=…`. The server expects that value on `Authorization: Bearer`; in Swagger use Authorize and paste the same secret.

If you are **already** in a clone of this repo, do **not** run `git clone` again (that nests a second copy inside the first). Only use `git clone` / `cd` on a fresh machine.

```bash
git clone https://github.com/bbartling/diy-bacnet-server.git
cd diy-bacnet-server
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
printf 'BACNET_RPC_API_KEY=%s\n' "$(openssl rand -hex 32)" > .env
set -a && . ./.env && set +a
python -m bacpypes_server.main --name asdf --instance 123456 --address 192.168.204.18/24:47808 --public --debug
```

With `--public`, open `http://127.0.0.1:8080/docs` (or this host’s LAN IP from another machine). `POST /server_hello` stays unauthenticated; other JSON-RPC routes need Bearer when a key is set. Who-Is and discovery match bacpypes3 once UDP 47808 is allowed through the host firewall. Skip `.env` only for unsecured loopback tests.

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

## License

MIT. See `LICENSE`.
