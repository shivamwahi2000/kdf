"""PostgreSQL connector implementation."""

from typing import Any, Dict
from pyspark.sql import DataFrame

from kdf.connectors.base import Connector
from kdf.connectors.postgres.config import PostgresConfig
from kdf.connectors.postgres.auth import PostgresAuth
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import ConnectionError as KDFConnectionError, SchemaError


class PostgresConnector(Connector):
    """PostgreSQL connector using JDBC."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize PostgreSQL connector."""
        super().__init__(config)

        # Parse connection if provided
        if config.get("connection"):
            connection_params = PostgresAuth.from_connection_string(config["connection"])
            config.update({k: v for k, v in connection_params.items() if v is not None})

        self.pg_config = PostgresConfig(**config)

    def validate_connection(self, context: ExecutionContext) -> bool:
        """Validate PostgreSQL connection."""
        try:
            # Try to read just one row to validate connection
            test_query = f"(SELECT 1 FROM {self.pg_config.get_full_table_name()} LIMIT 1) AS test"
            user, password = self.pg_config.get_credentials()

            context.spark.read.format("jdbc") \
                .option("url", self.pg_config.get_jdbc_url()) \
                .option("dbtable", test_query) \
                .option("user", user) \
                .option("password", password) \
                .load() \
                .collect()

            return True
        except Exception as e:
            raise KDFConnectionError(f"PostgreSQL connection failed: {e}") from e

    def discover_schema(self, context: ExecutionContext) -> Dict[str, Any]:
        """Discover schema from PostgreSQL table."""
        try:
            # Read schema without loading data
            df = self._create_reader(context, limit=0)
            schema = df.schema

            return {
                "table": self.pg_config.get_full_table_name(),
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
        """Read data from PostgreSQL."""
        return self._create_reader(context)

    def _create_reader(self, context: ExecutionContext, limit: int = None) -> DataFrame:
        """Create Spark JDBC reader for PostgreSQL."""
        user, password = self.pg_config.get_credentials()

        # Build table reference or query
        if limit is not None:
            dbtable = f"(SELECT * FROM {self.pg_config.get_full_table_name()} LIMIT {limit}) AS limited"
        else:
            dbtable = self.pg_config.get_full_table_name()

        reader = (
            context.spark.read.format("jdbc")
            .option("url", self.pg_config.get_jdbc_url())
            .option("dbtable", dbtable)
            .option("user", user)
            .option("password", password)
            .option("fetchsize", self.pg_config.fetch_size)
        )

        # Configure partitioned reads if partition column specified
        if self.pg_config.partition_column:
            reader = reader \
                .option("partitionColumn", self.pg_config.partition_column) \
                .option("numPartitions", self.pg_config.num_partitions)

            if self.pg_config.lower_bound is not None:
                reader = reader.option("lowerBound", self.pg_config.lower_bound)
            if self.pg_config.upper_bound is not None:
                reader = reader.option("upperBound", self.pg_config.upper_bound)

        return reader.load()

    def metadata(self, context: ExecutionContext) -> Dict[str, Any]:
        """Get PostgreSQL metadata."""
        return {
            "connector": "postgres",
            "host": self.pg_config.host or "from_env",
            "database": self.pg_config.database,
            "schema": self.pg_config.schema,
            "table": self.pg_config.table,
            "jdbc_url": self.pg_config.get_jdbc_url(),
        }
