"""Kafka connector for streaming data."""

from kdf.connectors.kafka.connector import KafkaConnector
from kdf.connectors.kafka.config import KafkaConfig

__all__ = ["KafkaConnector", "KafkaConfig"]
