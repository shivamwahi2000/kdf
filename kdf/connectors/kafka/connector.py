"""Kafka connector implementation."""

from typing import Any, Dict
from pyspark.sql import DataFrame
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import StructType

from kdf.connectors.base import Connector
from kdf.connectors.kafka.config import KafkaConfig
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import ConnectionError as KDFConnectionError, SchemaError


class KafkaConnector(Connector):
    """Kafka connector for streaming data ingestion."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Kafka connector."""
        super().__init__(config)
        self.kafka_config = KafkaConfig(**config)

    def validate_connection(self, context: ExecutionContext) -> bool:
        """Validate Kafka connection.

        Note: This is a lightweight check. Full validation happens at stream start.
        """
        try:
            # For streaming, we can't easily validate without starting a stream
            # Just validate configuration is complete
            self.kafka_config.get_kafka_options()
            return True
        except Exception as e:
            raise KDFConnectionError(f"Kafka configuration validation failed: {e}") from e

    def discover_schema(self, context: ExecutionContext) -> Dict[str, Any]:
        """Discover schema from Kafka messages.

        Note: For Kafka, schema discovery is limited since messages are typically
        JSON/Avro and schema is not available until messages are consumed.
        """
        return {
            "connector": "kafka",
            "topic": self.kafka_config.topic,
            "format": self.kafka_config.value_format,
            "note": "Schema will be inferred from messages or must be provided"
        }

    def read(self, context: ExecutionContext) -> DataFrame:
        """Read from Kafka as a streaming DataFrame.

        Note: This returns a streaming DataFrame. For batch use cases,
        consider using a different connector or implementing batch read logic.
        """
        return self.read_stream(context)

    def read_stream(self, context: ExecutionContext) -> DataFrame:
        """Read Kafka as a stream."""
        reader = context.spark.readStream.format("kafka")

        # Apply Kafka options
        options = self.kafka_config.get_kafka_options()
        for key, value in options.items():
            reader = reader.option(key, value)

        # Read stream
        df = reader.load()

        # Parse message value based on format
        if self.kafka_config.value_format == "json":
            # Cast value to string and parse as JSON
            # User should provide schema or use schema inference in skill
            df = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)", "topic", "partition", "offset", "timestamp")
        elif self.kafka_config.value_format == "string":
            # Simple string conversion
            df = df.selectExpr("CAST(key AS STRING)", "CAST(value AS STRING)", "topic", "partition", "offset", "timestamp")
        # For Avro and other formats, additional processing would be needed

        return df

    def metadata(self, context: ExecutionContext) -> Dict[str, Any]:
        """Get Kafka metadata."""
        return {
            "connector": "kafka",
            "bootstrap_servers": self.kafka_config.bootstrap_servers,
            "topic": self.kafka_config.topic,
            "group_id": self.kafka_config.group_id,
            "starting_offsets": self.kafka_config.starting_offsets,
            "security_protocol": self.kafka_config.security_protocol,
        }
