# DIY Edge Lambda — Agents Guide

## Overview

This ecosystem provides a practical, local-first, docker-friendly platform for smart-building edge automation.

* diy-bacnet-server
  FastAPI + BACpypes3 BACnet/IP server exposing a JSON-RPC API for reading, writing, supervising BACnet devices at the edge.

* diy-edge-lambda-manager
  A local AWS-Lambda-style runtime for IoT edge. Upload Python agent bundles, run them as isolated OS processes, stop/restart them, monitor logs, all through Swagger UI.

* diy-edge-lambda-agents
  Developer toolkit and collection of ready-made agents. Build, package, and deploy optimization agents, testing tools, supervisory control bots, and FDD logic workloads.


* **[diy-bacnet-server](https://github.com/bbartling/diy-bacnet-server)** — a lightweight FastAPI + bacpypes3 BACnet/IP server that exposes a JSON-RPC API for reading, writing, and supervising BACnet devices at the edge.
* **[diy-edge-lambda-agents](https://github.com/bbartling/diy-edge-lambda-agents)** — a collection of edge “Lambda-style” HVAC optimization agents (optimal start, Guideline 36, FDD tools, testing agents, etc.) packaged as deployable ZIP workloads.
* **[diy-edge-lambda-manager](https://github.com/bbartling/diy-edge-lambda-manager)** — a local “AWS Lambda-like” runtime for the edge that lets you upload, run, stop, and monitor agents via a clean FastAPI + Swagger UI, using real Linux subprocess execution under the hood.


This stack enables serious automation at the building edge without cloud dependency. It is intended for real systems, lab environments, pilots, research, and production deployments.

---

## What is an Edge Agent?

An Agent is a packaged Python workload that runs independently on the edge:

* packaged as a ZIP bundle
* uploaded to the Edge Lambda Manager
* executed as its own isolated Linux process
* each agent runs with its own interpreter environment
* supports multiple agents in parallel
* logs are retrievable and viewable
* can run for long-duration supervisory work
* suitable for FDD, analytics, control strategies, testing tools, and experiments

---

## Agent Structure

Each agent lives in its own folder under `agents/`:

```
agents/
  my_agent/
    lambda_function.py
    config.json
    requirements.txt
    dist/
```

### Required

`lambda_function.py`
Must provide:

```python
def handler(event=None, context=None):
    ...
```

### Optional

`config.json`

```
{
  "bacnet_base_url": "http://YOUR_EDGE_SERVER:8080",
  "interval_seconds": 15
}
```

`requirements.txt`
Standard Python dependency list.

---

## Packaging and Deployment

Agents follow an AWS-style packaging approach:

```
pip install -r requirements.txt -t dist/
copy lambda_function.py dist/
cd dist
zip -r my_agent.zip .
```

Upload via:

* Edge Lambda Manager Swagger UI
  or
* HTTP API

The Edge Manager runs each agent:

* as a real OS subprocess
* under real Linux scheduling
* fully isolated
* stable even when multiple workloads run concurrently

---

## Docker Best Practices

### Why Docker Matters

* predictable and reproducible builds
* architecture correctness (especially ARM vs x86)
* prevents dependency drift
* isolates Python environments cleanly
* ensures compatibility between development and deployment devices
* supports multi-architecture images
* avoids “works on my machine” issues

### Multi-Architecture Builds

Example:

```
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t myagent:latest .
```

Building agents inside Docker ensures bundled dependencies match:

* target OS
* target architecture
* Python version

If you build agents on Windows, WSL, or Mac, Docker ensures they deploy correctly on Raspberry Pi or other ARM edge systems.

---

## Example Applications

This framework is appropriate for building:

* Guideline 36 supervisory optimization logic
* Optimal Start / Optimal Stop agents
* HVAC energy optimization controllers
* Fault Detection and Diagnostics tools
* Safety / watchdog supervisory agents
* BACnet testing and validation bots
* simulation or research agents
* “chaos testing” workloads
* cybersecurity monitoring agents
* production optimization intelligence

---

## Design Philosophy

The system is designed to be:

* local-first
* resilient
* transparent
* open
* flexible
* suitable for both engineers and researchers
* straightforward to extend

It intentionally removes vendor lock-in and provides a practical way to innovate directly on the building edge.

---

## Future Possibilities

* agent templates / scaffolding tools
* historical logging and analytics backend
* built-in ML agent support
* distributed multi-building coordination
* automated deployment workflows
* curated public agent library
* additional reference HVAC optimization agents

---

## Community Direction

This ecosystem is intended to help:

* BAS engineers
* system integrators
* energy researchers
* software developers
* students and innovators

It provides an open platform for experimentation, learning, and professional deployment of modern building intelligence.

If you build useful agents or improvements, please consider sharing them.


