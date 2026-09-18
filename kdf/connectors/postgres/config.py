"""PostgreSQL connector configuration."""

import os
from typing import Optional
from pydantic import BaseModel, Field


class PostgresConfig(BaseModel):
    """PostgreSQL connection configuration."""

    host: Optional[str] = None
    port: int = 5432
    database: Optional[str] = None
    schema: str = "public"
    table: str
    user: Optional[str] = None
    password: Optional[str] = None
    connection: Optional[str] = None

    # JDBC options
    fetch_size: int = 10000
    partition_column: Optional[str] = None
    num_partitions: int = 4
    lower_bound: Optional[int] = None
    upper_bound: Optional[int] = None

    # SSL
    ssl_enabled: bool = False
    ssl_mode: str = "prefer"

    # Advanced
    session_init_statement: Optional[str] = None
    query_timeout: int = 600

    def get_jdbc_url(self) -> str:
        """Construct JDBC URL."""
        host = self.host or os.getenv("POSTGRES_HOST", "localhost")
        database = self.database or os.getenv("POSTGRES_DATABASE", "postgres")

        url = f"jdbc:postgresql://{host}:{self.port}/{database}"

        if self.ssl_enabled:
            url += f"?ssl=true&sslmode={self.ssl_mode}"

        return url

    def get_credentials(self) -> tuple[str, str]:
        """Get credentials from config or environment."""
        user = self.user or os.getenv("POSTGRES_USER", "")
        password = self.password or os.getenv("POSTGRES_PASSWORD", "")
        return user, password

    def get_full_table_name(self) -> str:
        """Get fully qualified table name."""
        return f"{self.schema}.{self.table}"
