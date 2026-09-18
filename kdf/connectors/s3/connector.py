"""S3 connector implementation."""

from typing import Any, Dict
from pyspark.sql import DataFrame

from kdf.connectors.base import Connector
from kdf.connectors.s3.config import S3Config
from kdf.connectors.s3.auth import S3Auth
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import ConnectionError as KDFConnectionError, SchemaError


class S3Connector(Connector):
    """S3 connector for reading various file formats."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize S3 connector."""
        super().__init__(config)
        self.s3_config = S3Config(**config)

    def validate_connection(self, context: ExecutionContext) -> bool:
        """Validate S3 connection and path."""
        try:
            # Configure credentials
            access_key, secret_key = self.s3_config.get_credentials()
            if access_key and secret_key:
                S3Auth.configure_spark(context.spark, access_key, secret_key)

            # Try to list files at path to validate access
            # This is a lightweight check
            hadoop_conf = context.spark.sparkContext._jsc.hadoopConfiguration()
            hadoop_fs = context.spark._jvm.org.apache.hadoop.fs.FileSystem.get(
                context.spark._jvm.java.net.URI(self.s3_config.path),
                hadoop_conf
            )

            path = context.spark._jvm.org.apache.hadoop.fs.Path(self.s3_config.path)
            exists = hadoop_fs.exists(path)

            if not exists:
                raise KDFConnectionError(f"S3 path does not exist: {self.s3_config.path}")

            return True
        except Exception as e:
            raise KDFConnectionError(f"S3 connection failed: {e}") from e

    def discover_schema(self, context: ExecutionContext) -> Dict[str, Any]:
        """Discover schema from S3 files."""
        try:
            # Read a sample to infer schema
            df = self._create_reader(context).limit(0)
            schema = df.schema

            return {
                "path": self.s3_config.path,
                "format": self.s3_config.format,
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
            raise SchemaError(f"Schema discovery failed: {e}") from e

    def read(self, context: ExecutionContext) -> DataFrame:
        """Read data from S3."""
        # Configure credentials if provided
        access_key, secret_key = self.s3_config.get_credentials()
        if access_key and secret_key:
            S3Auth.configure_spark(context.spark, access_key, secret_key)

        return self._create_reader(context)

    def _create_reader(self, context: ExecutionContext) -> DataFrame:
        """Create Spark reader for S3."""
        # Normalize format (jsonl -> json)
        format_name = "json" if self.s3_config.format == "jsonl" else self.s3_config.format

        reader = context.spark.read.format(format_name)

        # Apply format-specific options
        options = self.s3_config.get_format_options()
        for key, value in options.items():
            reader = reader.option(key, value)

        return reader.load(self.s3_config.path)

    def metadata(self, context: ExecutionContext) -> Dict[str, Any]:
        """Get S3 metadata."""
        return {
            "connector": "s3",
            "path": self.s3_config.path,
            "format": self.s3_config.format,
            "region": self.s3_config.get_region(),
        }
