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

Full documentation is in:

- [`docs/index.md`](docs/index.md)

This includes API auth, CSV schema, schedule RPC, MQTT schema/topics, Modbus endpoint, Docker operations, and testing workflows.

## License

MIT. See `LICENSE`.
