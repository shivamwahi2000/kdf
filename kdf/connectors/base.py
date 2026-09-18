"""Base connector interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pyspark.sql import DataFrame

from kdf.core.context import ExecutionContext


class Connector(ABC):
    """Base class for all KDF connectors."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize connector.

        Args:
            config: Connector configuration
        """
        self.config = config
        self.name = config.get("type", self.__class__.__name__)

    @abstractmethod
    def validate_connection(self, context: ExecutionContext) -> bool:
        """Validate connection to data source.

        Args:
            context: Execution context

        Returns:
            True if connection is valid

        Raises:
            ConnectionError: If connection fails
        """
        pass

    @abstractmethod
    def discover_schema(self, context: ExecutionContext) -> Dict[str, Any]:
        """Discover schema from data source.

        Args:
            context: Execution context

        Returns:
            Schema information

        Raises:
            SchemaError: If schema discovery fails
        """
        pass

    @abstractmethod
    def read(self, context: ExecutionContext) -> DataFrame:
        """Read data from source.

        Args:
            context: Execution context

        Returns:
            DataFrame containing source data

        Raises:
            KDFException: If read fails
        """
        pass

    @abstractmethod
    def metadata(self, context: ExecutionContext) -> Dict[str, Any]:
        """Get metadata about the data source.

        Args:
            context: Execution context

        Returns:
            Metadata dictionary
        """
        pass
