"""Pipeline run metadata store."""

from typing import List, Optional
from datetime import datetime
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, TimestampType, IntegerType
from pyspark.sql.functions import col

from kdf.core.models import PipelineRun, PipelineStatus


class RunMetadataStore:
    """Store and query pipeline run metadata."""

    def __init__(self, spark: SparkSession, base_path: str = "./kdf_metadata"):
        """Initialize run metadata store.

        Args:
            spark: Spark session
            base_path: Base path for metadata storage
        """
        self.spark = spark
        self.metadata_path = f"{base_path}/pipeline_runs"
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Ensure metadata table exists."""
        try:
            self.spark.read.format("delta").load(self.metadata_path)
        except Exception:
            # Create table
            schema = StructType([
                StructField("run_id", StringType(), False),
                StructField("pipeline_name", StringType(), False),
                StructField("status", StringType(), False),
                StructField("start_time", TimestampType(), False),
                StructField("end_time", TimestampType(), True),
                StructField("records_read", IntegerType(), True),
                StructField("records_written", IntegerType(), True),
                StructField("records_failed", IntegerType(), True),
                StructField("source", StringType(), True),
                StructField("target", StringType(), True),
                StructField("error_message", StringType(), True),
                StructField("metadata_json", StringType(), True),
            ])

            empty_df = self.spark.createDataFrame([], schema)
            empty_df.write.format("delta").save(self.metadata_path)

    def save_run(self, run: PipelineRun) -> None:
        """Save pipeline run metadata.

        Args:
            run: Pipeline run to save
        """
        import json

        run_data = [(
            run.run_id,
            run.pipeline_name,
            run.status.value,
            run.start_time,
            run.end_time,
            run.records_read,
            run.records_written,
            run.records_failed,
            run.source,
            run.target,
            run.error_message,
            json.dumps(run.metadata),
        )]

        schema = StructType([
            StructField("run_id", StringType(), False),
            StructField("pipeline_name", StringType(), False),
            StructField("status", StringType(), False),
            StructField("start_time", TimestampType(), False),
            StructField("end_time", TimestampType(), True),
            StructField("records_read", IntegerType(), True),
            StructField("records_written", IntegerType(), True),
            StructField("records_failed", IntegerType(), True),
            StructField("source", StringType(), True),
            StructField("target", StringType(), True),
            StructField("error_message", StringType(), True),
            StructField("metadata_json", StringType(), True),
        ])

        df = self.spark.createDataFrame(run_data, schema)
        df.write.format("delta").mode("append").save(self.metadata_path)

    def get_run(self, run_id: str) -> Optional[PipelineRun]:
        """Get pipeline run by ID.

        Args:
            run_id: Run identifier

        Returns:
            Pipeline run or None
        """
        df = self.spark.read.format("delta").load(self.metadata_path)
        result = df.filter(col("run_id") == run_id).collect()

        if not result:
            return None

        row = result[0]
        return self._row_to_run(row)

    def get_pipeline_history(self, pipeline_name: str, limit: int = 10) -> List[PipelineRun]:
        """Get recent runs for a pipeline.

        Args:
            pipeline_name: Pipeline name
            limit: Maximum number of runs to return

        Returns:
            List of pipeline runs
        """
        df = self.spark.read.format("delta").load(self.metadata_path)
        results = (
            df.filter(col("pipeline_name") == pipeline_name)
            .orderBy(col("start_time").desc())
            .limit(limit)
            .collect()
        )

        return [self._row_to_run(row) for row in results]

    def _row_to_run(self, row) -> PipelineRun:
        """Convert Row to PipelineRun."""
        import json

        return PipelineRun(
            run_id=row["run_id"],
            pipeline_name=row["pipeline_name"],
            status=PipelineStatus(row["status"]),
            start_time=row["start_time"],
            end_time=row["end_time"],
            records_read=row["records_read"],
            records_written=row["records_written"],
            records_failed=row["records_failed"],
            source=row["source"],
            target=row["target"],
            error_message=row["error_message"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else {},
        )
