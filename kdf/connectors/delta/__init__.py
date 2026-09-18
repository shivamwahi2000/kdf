"""Delta Lake connector."""

from kdf.connectors.delta.connector import DeltaConnector
from kdf.connectors.delta.config import DeltaConfig

__all__ = ["DeltaConnector", "DeltaConfig"]
