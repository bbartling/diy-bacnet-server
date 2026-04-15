## diy-bacnet-server

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

## Documentation

- **Published site:** [bbartling.github.io/diy-bacnet-server](https://bbartling.github.io/diy-bacnet-server/)
- **Source (Just the Docs):** start at [`docs/index.md`](docs/index.md); topic pages live alongside it under `docs/*.md` (same multi-page style as [easy-aso](https://github.com/bbartling/easy-aso/tree/master/docs)).

## License

MIT. See `LICENSE`.
