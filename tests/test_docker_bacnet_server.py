import subprocess
import time
import os
import pytest


COMPOSE_FILE = os.path.join(os.path.dirname(__file__), "docker-compose.yml")
SERVICE_NAME = "diy-bacnet-server-test"


@pytest.fixture(scope="module")
def run_docker_compose():
    """Start the BACnet server container for the duration of the test module."""
    # docker-compose up
    subprocess.run(
        ["docker-compose", "-f", COMPOSE_FILE, "up", "-d"],
        check=True,
    )
    # give container some time to start BACnet stack and JSON-RPC API
    time.sleep(15)
    yield
    # docker-compose down
    subprocess.run(
        ["docker-compose", "-f", COMPOSE_FILE, "down"],
        check=True,
    )


def _get_container_logs(name: str) -> str:
    proc = subprocess.run(
        ["docker", "logs", name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return proc.stdout


def test_bacnet_server_startup(run_docker_compose):
    """Basic smoke test that container starts and BACnet/JSON-RPC boot without exceptions."""
    logs = _get_container_logs(SERVICE_NAME)

    # Helpful debug print if the test fails in CI
    print("===== diy-bacnet-server container logs =====")
    print(logs)
    print("===========================================")

    # Ensure the BACpypes application initialized
    assert "BACnet application initialized." in logs

    # Ensure the JSON-RPC API came up
    assert "JSON-RPC API ready at" in logs

    # No unhandled tracebacks or import errors allowed in logs
    assert "Traceback (most recent call last)" not in logs
    assert "ModuleNotFoundError" not in logs
    assert "ImportError" not in logs
