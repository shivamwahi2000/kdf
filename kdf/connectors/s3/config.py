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

    # Autoloader configuration (cloudFiles)
    use_autoloader: bool = True  # Use Autoloader by default for incremental/streaming
    schema_location: Optional[str] = None  # Required for Autoloader, auto-generated if None
    schema_evolution_mode: str = "addNewColumns"  # rescue, failOnNewColumns, addNewColumns
    infer_column_types: bool = True
    max_files_per_trigger: Optional[int] = None
    max_bytes_per_trigger: Optional[str] = None
    include_existing_files: bool = True
    use_notifications: bool = False  # Use cloud notifications for near-instant processing

    # Rescue data (for malformed records)
    rescue_data_column: Optional[str] = "_rescued_data"

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
        """Get format-specific options for standard batch read."""
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

    def get_autoloader_options(self, checkpoint_base: str = "/tmp/kdf/checkpoints") -> dict:
        """Get Autoloader (cloudFiles) specific options."""
        # Normalize format (jsonl -> json)
        format_name = "json" if self.format == "jsonl" else self.format

        options = dict(self.options)
        options["cloudFiles.format"] = format_name

        # Schema location (required for Autoloader)
        if self.schema_location:
            options["cloudFiles.schemaLocation"] = self.schema_location
        else:
            # Auto-generate from path
            import hashlib
            path_hash = hashlib.md5(self.path.encode()).hexdigest()[:8]
            options["cloudFiles.schemaLocation"] = f"{checkpoint_base}/schema/{path_hash}"

        # Schema evolution
        options["cloudFiles.schemaEvolutionMode"] = self.schema_evolution_mode
        options["cloudFiles.inferColumnTypes"] = str(self.infer_column_types).lower()

        # Performance tuning
        if self.max_files_per_trigger:
            options["cloudFiles.maxFilesPerTrigger"] = str(self.max_files_per_trigger)
        if self.max_bytes_per_trigger:
            options["cloudFiles.maxBytesPerTrigger"] = self.max_bytes_per_trigger

        # Include existing files on first run
        options["cloudFiles.includeExistingFiles"] = str(self.include_existing_files).lower()

        # Use cloud notifications for near-instant processing
        if self.use_notifications:
            options["cloudFiles.useNotifications"] = "true"

        # Rescue data column for malformed records
        if self.rescue_data_column:
            options["rescuedDataColumn"] = self.rescue_data_column

        # Path filtering
        if self.path_glob_filter:
            options["cloudFiles.pathGlobFilter"] = self.path_glob_filter

        # Format-specific options for Autoloader
        if self.format == "csv":
            options["header"] = str(self.header).lower()
        elif self.format in ["json", "jsonl"]:
            options["multiLine"] = str(self.multiline).lower()

        return options
