"""bacpypes_server.env_features."""

from bacpypes_server.env_features import (
    apply_openapi_docs_default_from_public,
    openapi_docs_enabled,
)


def test_apply_default_public_sets_true(monkeypatch):
    monkeypatch.delenv("BACNET_ENABLE_OPENAPI_DOCS", raising=False)
    apply_openapi_docs_default_from_public(True)
    assert openapi_docs_enabled() is True


def test_apply_default_nonpublic_sets_false(monkeypatch):
    monkeypatch.delenv("BACNET_ENABLE_OPENAPI_DOCS", raising=False)
    apply_openapi_docs_default_from_public(False)
    assert openapi_docs_enabled() is False


def test_apply_default_skips_when_bacnet_preset(monkeypatch):
    monkeypatch.setenv("BACNET_ENABLE_OPENAPI_DOCS", "false")
    apply_openapi_docs_default_from_public(True)
    assert openapi_docs_enabled() is False


def test_openapi_docs_bacnet_true(monkeypatch):
    monkeypatch.setenv("BACNET_ENABLE_OPENAPI_DOCS", "true")
    monkeypatch.delenv("OFDD_ENABLE_OPENAPI_DOCS", raising=False)
    assert openapi_docs_enabled() is True


def test_openapi_docs_bacnet_false_ignores_ofdd(monkeypatch):
    monkeypatch.setenv("BACNET_ENABLE_OPENAPI_DOCS", "false")
    monkeypatch.setenv("OFDD_ENABLE_OPENAPI_DOCS", "true")
    assert openapi_docs_enabled() is False


def test_openapi_docs_legacy_ofdd_when_bacnet_absent(monkeypatch):
    monkeypatch.delenv("BACNET_ENABLE_OPENAPI_DOCS", raising=False)
    monkeypatch.setenv("OFDD_ENABLE_OPENAPI_DOCS", "yes")
    assert openapi_docs_enabled() is True
