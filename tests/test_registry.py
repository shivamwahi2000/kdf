"""Tests for registry module."""

import pytest
from kdf.core.registry import Registry, ConnectorRegistry, SkillRegistry
from kdf.core.exceptions import RegistryError


def test_basic_registry():
    """Test basic registry operations."""
    registry = Registry()

    # Register item
    registry.register("test_item", "test_value")

    # Get item
    assert registry.get("test_item") == "test_value"

    # List items
    assert "test_item" in registry.list()

    # Has item
    assert registry.has("test_item")
    assert not registry.has("nonexistent")


def test_duplicate_registration():
    """Test that duplicate registration raises error."""
    registry = Registry()
    registry.register("test", "value1")

    with pytest.raises(RegistryError):
        registry.register("test", "value2")


def test_get_nonexistent():
    """Test getting nonexistent item raises error."""
    registry = Registry()

    with pytest.raises(RegistryError):
        registry.get("nonexistent")


def test_connector_registry():
    """Test connector registry."""

    class MockConnector:
        def __init__(self, config):
            self.config = config

    registry = ConnectorRegistry()
    registry.register_connector("mock", MockConnector)

    connector = registry.create_connector("mock", {"test": "config"})
    assert isinstance(connector, MockConnector)
    assert connector.config == {"test": "config"}
