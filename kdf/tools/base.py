"""Base tool interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from pydantic import BaseModel

from kdf.core.models import ToolInput, ToolOutput


class Tool(ABC):
    """Base class for agent tools."""

    def __init__(self):
        """Initialize tool."""
        self.name = self.__class__.__name__

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for agents."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> List[ToolInput]:
        """Define input parameters."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolOutput:
        """Execute tool.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool output with data or error
        """
        pass

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation."""
        return {
            "name": self.name,
            "description": self.description,
            "inputs": [
                {
                    "name": inp.name,
                    "description": inp.description,
                    "type": inp.type,
                    "required": inp.required,
                }
                for inp in self.input_schema
            ],
        }
