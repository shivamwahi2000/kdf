"""Core data models for KDF."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class SchemaChangeType(str, Enum):
    """Schema change classification."""
    COMPATIBLE = "COMPATIBLE"
    WARNING = "WARNING"
    BREAKING = "BREAKING"


class QualityStatus(str, Enum):
    """Data quality check status."""
    PASSED = "PASSED"
    FAILED = "FAILED"
    WARNING = "WARNING"


class PermissionLevel(str, Enum):
    """Agent permission levels."""
    READ_ONLY = "READ_ONLY"
    ANALYZE = "ANALYZE"
    EXECUTE_APPROVED = "EXECUTE_APPROVED"
    AUTONOMOUS = "AUTONOMOUS"


class PipelineRun(BaseModel):
    """Pipeline execution run metadata."""
    run_id: str
    pipeline_name: str
    status: PipelineStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    records_read: Optional[int] = None
    records_written: Optional[int] = None
    records_failed: Optional[int] = None
    source: Optional[str] = None
    target: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Watermark(BaseModel):
    """Watermark for incremental processing."""
    pipeline_name: str
    column_name: str
    value: Any
    updated_at: datetime


class SchemaChange(BaseModel):
    """Schema change detection result."""
    column_name: str
    change_type: SchemaChangeType
    old_type: Optional[str] = None
    new_type: Optional[str] = None
    description: str


class QualityResult(BaseModel):
    """Data quality check result."""
    check_name: str
    status: QualityStatus
    column: Optional[str] = None
    violations: int = 0
    total_records: int = 0
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ReconciliationResult(BaseModel):
    """Reconciliation check result."""
    source_records: int
    target_records: int
    difference: int
    source_duplicates: int = 0
    target_duplicates: int = 0
    match_rate: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SkillMetrics(BaseModel):
    """Metrics from skill execution."""
    skill_name: str
    input_records: int
    output_records: int
    duration_seconds: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ToolInput(BaseModel):
    """Input schema for a tool."""
    name: str
    description: str
    type: str
    required: bool = True


class ToolOutput(BaseModel):
    """Output from tool execution."""
    success: bool
    data: Any
    error: Optional[str] = None


class AgentPermissions(BaseModel):
    """Agent skill permissions."""
    metadata_read: bool = True
    source_data_read: bool = False
    target_data_read: bool = False
    target_data_write: bool = False
    pipeline_execution: bool = False
    infrastructure_modify: bool = False


class ExecutionMode(str, Enum):
    """Pipeline execution mode."""
    BATCH = "batch"
    MICRO_BATCH = "micro_batch"
    STREAMING = "streaming"


class MedallionLayer(str, Enum):
    """Medallion architecture layer."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    CUSTOM = "custom"


class PipelineDependency(BaseModel):
    """Pipeline dependency specification."""
    pipeline_name: str
    wait_for_completion: bool = True


class MedallionConfig(BaseModel):
    """Medallion architecture configuration."""
    layer: MedallionLayer
    upstream_layers: List[str] = Field(default_factory=list)
    quality_level: Optional[str] = None  # e.g., "validated", "enriched"
    description: Optional[str] = None
