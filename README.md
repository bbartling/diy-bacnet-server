## diy-bacnet-server

[![Discord](https://img.shields.io/badge/Discord-Join%20Server-5865F2.svg?logo=discord&logoColor=white)](https://discord.gg/Ta48yQF8fC)
[![CI](https://github.com/bbartling/diy-bacnet-server/actions/workflows/ci.yml/badge.svg)](https://github.com/bbartling/diy-bacnet-server/actions/workflows/ci.yml)
![MIT License](https://img.shields.io/badge/license-MIT-green.svg)
![Development Status](https://img.shields.io/badge/status-Beta-blue.svg)
![Python](https://img.shields.io/badge/Python-3.14-blue?logo=python&logoColor=white)

Lightweight BACnet/IP + JSON-RPC edge microservice for Docker-based deployments, including optional Modbus TCP client features.

## Quick Start

```bash
git clone https://github.com/bbartling/diy-bacnet-server.git
cd diy-bacnet-server
docker build -t diy-bacnet-server .
docker run --rm -it --network host --name bens-bacnet diy-bacnet-server \
  python3 -m bacpypes_server.main --name BensServer --instance 123456 --debug --public
```

- BACnet/IP: UDP `47808`
- JSON-RPC API: HTTP `8080`
- Swagger/OpenAPI: `/docs` and `/openapi.json` (when enabled by env)

## Local development

```bash
pip install -e ".[dev]"
python -m bacpypes_server.main --name Lab --instance 999 --debug
```

Dependencies and optional dev tools (`pytest`, `black`, …) live in **`pyproject.toml`** (PEP 621), not `requirements.txt`.

## Documentation

- **Published site:** [bbartling.github.io/diy-bacnet-server](https://bbartling.github.io/diy-bacnet-server/)
- **Source (Just the Docs):** start at [`docs/index.md`](docs/index.md); topic pages live alongside it under `docs/*.md` (same multi-page style as [easy-aso](https://github.com/bbartling/easy-aso/tree/master/docs)).

## License

MIT. See `LICENSE`.
