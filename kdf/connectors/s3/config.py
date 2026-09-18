"""S3 connector configuration."""

import os
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


class S3Config(BaseModel):
    """S3 connection configuration."""

    path: str
    format: str
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    region: Optional[str] = None
    endpoint: Optional[str] = None

    # Format-specific options
    header: bool = True  # CSV
    infer_schema: bool = True
    multiline: bool = False  # JSON
    merge_schema: bool = False  # Parquet

    # File discovery
    recursive: bool = False
    path_glob_filter: Optional[str] = None

    # Advanced
    options: dict = Field(default_factory=dict)

    @field_validator("format")
    @classmethod
    def validate_format(cls, v: str) -> str:
        """Validate file format."""
        allowed = ["csv", "json", "jsonl", "parquet"]
        if v.lower() not in allowed:
            raise ValueError(f"Format must be one of: {', '.join(allowed)}")
        return v.lower()

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate S3 path."""
        if not v.startswith("s3://") and not v.startswith("s3a://"):
            raise ValueError("Path must start with s3:// or s3a://")
        return v

    def get_credentials(self) -> tuple[Optional[str], Optional[str]]:
        """Get AWS credentials from config or environment."""
        access_key = self.access_key or os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = self.secret_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        return access_key, secret_key

    def get_region(self) -> Optional[str]:
        """Get AWS region."""
        return self.region or os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION"))

    def get_format_options(self) -> dict:
        """Get format-specific options."""
        options = dict(self.options)

        if self.format == "csv":
            options.setdefault("header", str(self.header).lower())
            options.setdefault("inferSchema", str(self.infer_schema).lower())
        elif self.format in ["json", "jsonl"]:
            options.setdefault("multiLine", str(self.multiline).lower())
        elif self.format == "parquet":
            options.setdefault("mergeSchema", str(self.merge_schema).lower())

        if self.path_glob_filter:
            options["pathGlobFilter"] = self.path_glob_filter

        if self.recursive:
            options["recursiveFileLookup"] = "true"

        return options
