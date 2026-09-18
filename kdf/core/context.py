"""Execution context for KDF pipelines."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pyspark.sql import SparkSession

from kdf.core.config import PipelineConfig
from kdf.core.models import PipelineRun, PipelineStatus


class ExecutionContext:
    """Execution context for a pipeline run."""

    def __init__(
        self,
        config: PipelineConfig,
        spark: Optional[SparkSession] = None,
        run_id: Optional[str] = None,
        metadata_path: Optional[str] = None,
    ):
        """Initialize execution context.

        Args:
            config: Pipeline configuration
            spark: Spark session (will create if not provided)
            run_id: Run ID (will generate if not provided)
            metadata_path: Path for metadata storage
        """
        self.config = config
        self.run_id = run_id or self._generate_run_id()
        self.metadata_path = metadata_path or "./kdf_metadata"

        # Initialize or use provided Spark session
        if spark:
            self.spark = spark
        else:
            self.spark = self._create_spark_session()

        # Runtime state
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.status = PipelineStatus.PENDING
        self.metrics: Dict[str, Any] = {}
        self.watermarks: Dict[str, Any] = {}
        self.errors: list[str] = []

    def _generate_run_id(self) -> str:
        """Generate unique run ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"{self.config.name}_{timestamp}_{unique_id}"

    def _create_spark_session(self) -> SparkSession:
        """Create Spark session with KDF defaults."""
        builder = (
            SparkSession.builder
            .appName(f"KDF: {self.config.name}")
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
            .config("spark.databricks.delta.schema.autoMerge.enabled", "true")
        )

        return builder.getOrCreate()

    def get_pipeline_run(self) -> PipelineRun:
        """Get current pipeline run metadata."""
        return PipelineRun(
            run_id=self.run_id,
            pipeline_name=self.config.name,
            status=self.status,
            start_time=self.start_time,
            end_time=self.end_time,
            records_read=self.metrics.get("records_read"),
            records_written=self.metrics.get("records_written"),
            records_failed=self.metrics.get("records_failed"),
            source=str(self.config.source.type),
            target=self.config.target.path,
            error_message="; ".join(self.errors) if self.errors else None,
            metadata=self.metrics,
        )

    def set_status(self, status: PipelineStatus) -> None:
        """Update pipeline status."""
        self.status = status
        if status in (PipelineStatus.SUCCESS, PipelineStatus.FAILED, PipelineStatus.CANCELLED):
            self.end_time = datetime.utcnow()

    def add_metric(self, key: str, value: Any) -> None:
        """Add a metric to the context."""
        self.metrics[key] = value

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)

    def get_watermark(self, key: str) -> Optional[Any]:
        """Get a watermark value."""
        return self.watermarks.get(key)

    def set_watermark(self, key: str, value: Any) -> None:
        """Set a watermark value."""
        self.watermarks[key] = value

    def __enter__(self):
        """Context manager entry."""
        self.set_status(PipelineStatus.RUNNING)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is not None:
            self.set_status(PipelineStatus.FAILED)
            self.add_error(str(exc_val))
        elif self.status == PipelineStatus.RUNNING:
            self.set_status(PipelineStatus.SUCCESS)
        return False
