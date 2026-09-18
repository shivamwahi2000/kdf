"""Kafka connector configuration."""

import os
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class KafkaConfig(BaseModel):
    """Kafka connection configuration."""

    bootstrap_servers: str
    topic: str
    group_id: Optional[str] = None

    # Starting offset
    starting_offsets: str = "latest"  # "latest", "earliest", or JSON offset spec

    # Security
    security_protocol: str = "PLAINTEXT"  # PLAINTEXT, SASL_PLAINTEXT, SASL_SSL, SSL
    sasl_mechanism: Optional[str] = None  # PLAIN, SCRAM-SHA-256, SCRAM-SHA-512
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None

    # Performance
    max_offsets_per_trigger: Optional[int] = None
    min_partitions: Optional[int] = None

    # Message format
    value_format: str = "json"  # json, avro, string
    key_deserializer: Optional[str] = None
    value_deserializer: Optional[str] = None

    # Advanced options
    options: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("bootstrap_servers")
    @classmethod
    def validate_servers(cls, v: str) -> str:
        """Validate bootstrap servers."""
        if not v or not v.strip():
            raise ValueError("Bootstrap servers cannot be empty")
        return v.strip()

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        """Validate topic name."""
        if not v or not v.strip():
            raise ValueError("Topic cannot be empty")
        return v.strip()

    def get_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Get Kafka credentials from config or environment."""
        username = self.sasl_username or os.getenv("KAFKA_USERNAME")
        password = self.sasl_password or os.getenv("KAFKA_PASSWORD")
        return username, password

    def get_kafka_options(self) -> Dict[str, Any]:
        """Get Kafka connection options."""
        options = {
            "kafka.bootstrap.servers": self.bootstrap_servers,
            "subscribe": self.topic,
            "startingOffsets": self.starting_offsets,
        }

        if self.group_id:
            options["kafka.group.id"] = self.group_id

        # Security configuration
        if self.security_protocol != "PLAINTEXT":
            options["kafka.security.protocol"] = self.security_protocol

        if self.sasl_mechanism:
            options["kafka.sasl.mechanism"] = self.sasl_mechanism
            username, password = self.get_credentials()
            if username and password:
                options["kafka.sasl.jaas.config"] = (
                    f'org.apache.kafka.common.security.plain.PlainLoginModule required '
                    f'username="{username}" password="{password}";'
                )

        # Performance options
        if self.max_offsets_per_trigger:
            options["maxOffsetsPerTrigger"] = str(self.max_offsets_per_trigger)

        if self.min_partitions:
            options["minPartitions"] = str(self.min_partitions)

        # Add custom options
        options.update(self.options)

        return options
