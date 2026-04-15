"""Shim for fastapi-jsonrpc on FastAPI >= 0.123.

FastAPI removed ``APIRoute.secure_cloned_response_field`` in favor of ``response_field``;
``fastapi-jsonrpc`` still passes ``field=self.secure_cloned_response_field`` into
``serialize_response``. Map the old name to ``response_field`` on ``MethodRoute`` only
when FastAPI is new enough, so older stacks are untouched.
"""

from __future__ import annotations

_applied = False


def _fastapi_version_tuple(version: str) -> tuple[int, ...]:
    base = version.split("+", 1)[0].strip()
    parts: list[int] = []
    for segment in base.split("."):
        if segment.isdigit():
            parts.append(int(segment))
        else:
            break
    return tuple(parts)


def apply_fastapi_jsonrpc_compat(jsonrpc_module) -> None:
    global _applied
    if _applied:
        return

    import fastapi

    if _fastapi_version_tuple(fastapi.__version__) < (0, 123):
        _applied = True
        return

    method_route_cls = jsonrpc_module.MethodRoute
    if getattr(method_route_cls, "_diy_bacnet_fastapi_jsonrpc_compat", False):
        _applied = True
        return

    method_route_cls.secure_cloned_response_field = property(
        lambda self: self.response_field  # type: ignore[attr-defined]
    )
    method_route_cls._diy_bacnet_fastapi_jsonrpc_compat = True  # type: ignore[attr-defined]
    _applied = True
