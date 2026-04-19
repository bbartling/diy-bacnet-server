"""Feature flags from the process environment."""

from __future__ import annotations

import os


def _truthy(raw: str) -> bool:
    return raw.strip().lower() in ("1", "true", "yes")


def apply_openapi_docs_default_from_public(public_http: bool) -> None:
    """If ``BACNET_ENABLE_OPENAPI_DOCS`` is unset, set it from ``--public`` (HTTP bind-all)."""
    if "BACNET_ENABLE_OPENAPI_DOCS" in os.environ:
        return
    os.environ["BACNET_ENABLE_OPENAPI_DOCS"] = "true" if public_http else "false"


def openapi_docs_enabled() -> bool:
    """Expose ``/docs``, ``/redoc``, ``/openapi.json`` when enabled.

    Uses ``BACNET_ENABLE_OPENAPI_DOCS`` when present (including ``false``).

    If that variable is absent, falls back to an alternate env key used by some
    older deployments.
    """
    if "BACNET_ENABLE_OPENAPI_DOCS" in os.environ:
        return _truthy(os.environ["BACNET_ENABLE_OPENAPI_DOCS"])
    return _truthy(os.environ.get("OFDD_ENABLE_OPENAPI_DOCS", ""))
