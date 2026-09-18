"""Delta Lake connector implementation."""

from typing import Any, Dict
from pyspark.sql import DataFrame

from kdf.connectors.base import Connector
from kdf.connectors.delta.config import DeltaConfig
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import ConnectionError as KDFConnectionError, SchemaError


class DeltaConnector(Connector):
    """Delta Lake connector for reading Delta tables."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Delta connector."""
        super().__init__(config)
        self.delta_config = DeltaConfig(**config)

    def validate_connection(self, context: ExecutionContext) -> bool:
        """Validate Delta table exists and is readable."""
        try:
            # Check if path exists and is a valid Delta table
            df = context.spark.read.format("delta").load(self.delta_config.path)
            # Try to get schema (lightweight operation)
            df.schema
            return True
        except Exception as e:
            raise KDFConnectionError(f"Delta table validation failed: {e}") from e

    def discover_schema(self, context: ExecutionContext) -> Dict[str, Any]:
        """Discover schema from Delta table."""
        try:
            df = self._create_reader(context).limit(0)
            schema = df.schema

            return {
                "path": self.delta_config.path,
                "format": "delta",
                "columns": [
                    {
                        "name": field.name,
                        "type": str(field.dataType),
                        "nullable": field.nullable,
                    }
                    for field in schema.fields
                ],
            }
        except Exception as e:
            raise SchemaError(f"Delta schema discovery failed: {e}") from e

    def read(self, context: ExecutionContext) -> DataFrame:
        """Read data from Delta table."""
        return self._create_reader(context)

    def _create_reader(self, context: ExecutionContext) -> DataFrame:
        """Create Spark reader for Delta table."""
        reader = context.spark.read.format("delta")

        # Apply read options
        options = self.delta_config.get_read_options()
        for key, value in options.items():
            reader = reader.option(key, value)

        # Time travel if specified
        if self.delta_config.version is not None:
            reader = reader.option("versionAsOf", self.delta_config.version)
        elif self.delta_config.timestamp:
            reader = reader.option("timestampAsOf", self.delta_config.timestamp)

        return reader.load(self.delta_config.path)

    def read_stream(self, context: ExecutionContext) -> DataFrame:
        """Read Delta table as a stream (for micro-batch/streaming)."""
        reader = context.spark.readStream.format("delta")

        # Apply streaming options
        options = self.delta_config.get_read_options()
        for key, value in options.items():
            reader = reader.option(key, value)

        return reader.load(self.delta_config.path)

    def metadata(self, context: ExecutionContext) -> Dict[str, Any]:
        """Get Delta table metadata."""
        metadata = {
            "connector": "delta",
            "path": self.delta_config.path,
            "streaming": self.delta_config.streaming,
        }

        # Get Delta table details
        try:
            delta_table = context.spark.sql(f"DESCRIBE DETAIL delta.`{self.delta_config.path}`")
            details = delta_table.collect()
            if details:
                row = details[0]
                metadata.update({
                    "format_version": row.get("format"),
                    "num_files": row.get("numFiles"),
                    "size_bytes": row.get("sizeInBytes"),
                    "partitioned_by": row.get("partitionColumns"),
                })
        except Exception:
            # Table might not exist yet or other issue
            pass

        return metadata
