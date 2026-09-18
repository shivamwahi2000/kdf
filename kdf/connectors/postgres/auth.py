"""PostgreSQL authentication handling."""

import os
from typing import Optional


class PostgresAuth:
    """PostgreSQL authentication manager."""

    @staticmethod
    def from_env() -> tuple[str, str]:
        """Load credentials from environment variables.

        Returns:
            (username, password) tuple
        """
        user = os.getenv("POSTGRES_USER", "")
        password = os.getenv("POSTGRES_PASSWORD", "")
        return user, password

    @staticmethod
    def from_connection_string(connection: str) -> dict:
        """Parse connection string.

        Args:
            connection: Connection string name or reference

        Returns:
            Connection parameters dictionary

        Note:
            This is a placeholder for future secret manager integration.
            In production, this would integrate with:
            - Databricks secrets
            - AWS Secrets Manager
            - Azure Key Vault
            - HashiCorp Vault
        """
        # For v0.1, support connection name that maps to env vars
        prefix = connection.upper().replace("-", "_")
        return {
            "host": os.getenv(f"{prefix}_HOST"),
            "port": int(os.getenv(f"{prefix}_PORT", "5432")),
            "database": os.getenv(f"{prefix}_DATABASE"),
            "user": os.getenv(f"{prefix}_USER"),
            "password": os.getenv(f"{prefix}_PASSWORD"),
        }
