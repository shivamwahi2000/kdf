"""Delta Lake connector configuration."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class DeltaConfig(BaseModel):
    """Delta Lake connection configuration."""

    path: str
    version: Optional[int] = None  # Time travel to specific version
    timestamp: Optional[str] = None  # Time travel to timestamp

    # Streaming options
    streaming: bool = False
    max_files_per_trigger: Optional[int] = None
    max_bytes_per_trigger: Optional[str] = None

    # Read options
    merge_schema: bool = False
    ignore_deletes: bool = False
    ignore_changes: bool = False

    # Advanced options
    options: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate Delta path."""
        if not v or not v.strip():
            raise ValueError("Delta path cannot be empty")
        return v.strip()

    def get_read_options(self) -> Dict[str, Any]:
        """Get Delta read options."""
        options = dict(self.options)

        if self.merge_schema:
            options["mergeSchema"] = "true"

        if self.ignore_deletes:
            options["ignoreDeletes"] = "true"

        if self.ignore_changes:
            options["ignoreChanges"] = "true"

        # Streaming options
        if self.streaming:
            if self.max_files_per_trigger:
                options["maxFilesPerTrigger"] = str(self.max_files_per_trigger)
            if self.max_bytes_per_trigger:
                options["maxBytesPerTrigger"] = self.max_bytes_per_trigger

        return options
