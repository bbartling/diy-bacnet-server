"""Tests for server_utils: supported point types and loader constants."""
import pytest

from bacpypes_server.server_utils import SUPPORTED_POINT_TYPES


def test_supported_point_types():
    """CSV loader supports normalized uppercase point type codes."""
    expected = {"AI", "AO", "AV", "BI", "BO", "BV", "MSI", "MSO", "MSV", "SCHEDULE"}
    assert SUPPORTED_POINT_TYPES == expected


def test_supported_point_types_count():
    """We support ten point type codes."""
    assert len(SUPPORTED_POINT_TYPES) == 10
