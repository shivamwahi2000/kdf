"""Registry for connectors, skills, and tools."""

from typing import Any, Callable, Dict, List, Optional, Type
from kdf.core.exceptions import RegistryError


class Registry:
    """Base registry for KDF components."""

    def __init__(self):
        """Initialize registry."""
        self._items: Dict[str, Any] = {}

    def register(self, name: str, item: Any) -> None:
        """Register an item.

        Args:
            name: Unique identifier
            item: Item to register

        Raises:
            RegistryError: If name already registered
        """
        if name in self._items:
            raise RegistryError(f"Item already registered: {name}")
        self._items[name] = item

    def get(self, name: str) -> Any:
        """Get registered item.

        Args:
            name: Item identifier

        Returns:
            Registered item

        Raises:
            RegistryError: If item not found
        """
        if name not in self._items:
            raise RegistryError(f"Item not registered: {name}")
        return self._items[name]

    def list(self) -> List[str]:
        """List all registered items."""
        return list(self._items.keys())

    def has(self, name: str) -> bool:
        """Check if item is registered."""
        return name in self._items


class ConnectorRegistry(Registry):
    """Registry for data connectors."""

    def register_connector(self, name: str, connector_class: Type) -> None:
        """Register a connector class."""
        self.register(name, connector_class)

    def create_connector(self, name: str, config: Dict[str, Any]) -> Any:
        """Create connector instance from config."""
        connector_class = self.get(name)
        return connector_class(config)


class SkillRegistry(Registry):
    """Registry for data skills."""

    def register_skill(self, name: str, skill_class: Type) -> None:
        """Register a skill class."""
        self.register(name, skill_class)

    def create_skill(self, name: str, config: Optional[Dict[str, Any]] = None) -> Any:
        """Create skill instance from config."""
        skill_class = self.get(name)
        return skill_class(config or {})


class ToolRegistry(Registry):
    """Registry for agent tools."""

    def register_tool(self, name: str, tool_class: Type) -> None:
        """Register a tool class."""
        self.register(name, tool_class)

    def get_tool(self, name: str) -> Any:
        """Get tool instance."""
        return self.get(name)


class AgentSkillRegistry(Registry):
    """Registry for agent skills."""

    def register_agent_skill(self, name: str, skill_path: str) -> None:
        """Register an agent skill by path."""
        self.register(name, skill_path)

    def get_agent_skill_path(self, name: str) -> str:
        """Get agent skill path."""
        return self.get(name)


# Global registries
connector_registry = ConnectorRegistry()
skill_registry = SkillRegistry()
tool_registry = ToolRegistry()
agent_skill_registry = AgentSkillRegistry()
