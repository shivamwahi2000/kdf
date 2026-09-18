"""Incremental load ingestion skill."""

from datetime import datetime
from typing import Optional
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, max as spark_max

from kdf.skills.base import DataSkill
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import SkillExecutionError, ConfigurationError


class IncrementalLoadSkill(DataSkill):
    """Incremental load using watermark column."""

    def validate_config(self) -> None:
        """Validate incremental load configuration."""
        if "column" not in self.config:
            raise ConfigurationError("Incremental load requires 'column' in configuration")

    def execute(self, df: DataFrame, context: ExecutionContext) -> DataFrame:
        """Execute incremental load.

        Args:
            df: Input DataFrame
            context: Execution context

        Returns:
            Filtered DataFrame containing only new/updated records

        Raises:
            SkillExecutionError: If execution fails
        """
        self.validate_config()

        column = self.config["column"]
        pipeline_name = context.config.name

        # Check if column exists
        if column not in df.columns:
            raise SkillExecutionError(
                f"Watermark column '{column}' not found in DataFrame. "
                f"Available columns: {', '.join(df.columns)}"
            )

        # Get last watermark from metadata
        last_watermark = self._get_last_watermark(context, pipeline_name, column)

        if last_watermark is None:
            # First run - load all data
            context.add_metric("incremental_first_run", True)
            filtered_df = df
        else:
            # Filter for records greater than last watermark
            # Use > for exclusive boundary to avoid duplicates
            context.add_metric("incremental_last_watermark", str(last_watermark))
            filtered_df = df.filter(col(column) > last_watermark)

        record_count = filtered_df.count()
        context.add_metric("incremental_records", record_count)

        if record_count > 0:
            # Calculate new watermark
            new_watermark = filtered_df.agg(spark_max(col(column))).collect()[0][0]
            self._save_watermark(context, pipeline_name, column, new_watermark)
            context.add_metric("incremental_new_watermark", str(new_watermark))
        else:
            context.add_metric("incremental_no_new_records", True)

        return filtered_df

    def _get_last_watermark(
        self,
        context: ExecutionContext,
        pipeline_name: str,
        column: str
    ) -> Optional[any]:
        """Get last watermark from metadata."""
        try:
            # Try to read from metadata table
            metadata_path = f"{context.metadata_path}/watermarks"
            watermarks_df = context.spark.read.format("delta").load(metadata_path)

            result = (
                watermarks_df
                .filter(
                    (col("pipeline_name") == pipeline_name) &
                    (col("column_name") == column)
                )
                .orderBy(col("updated_at").desc())
                .limit(1)
                .collect()
            )

            if result:
                return result[0]["value"]
            return None
        except Exception:
            # Metadata table doesn't exist yet (first run)
            return None

    def _save_watermark(
        self,
        context: ExecutionContext,
        pipeline_name: str,
        column: str,
        value: any
    ) -> None:
        """Save new watermark to metadata."""
        from pyspark.sql.types import StructType, StructField, StringType, TimestampType

        metadata_path = f"{context.metadata_path}/watermarks"

        # Create watermark record
        watermark_data = [(
            pipeline_name,
            column,
            str(value),  # Store as string for compatibility
            datetime.utcnow()
        )]

        schema = StructType([
            StructField("pipeline_name", StringType(), False),
            StructField("column_name", StringType(), False),
            StructField("value", StringType(), False),
            StructField("updated_at", TimestampType(), False),
        ])

        watermark_df = context.spark.createDataFrame(watermark_data, schema)

        # Append to metadata
        watermark_df.write.format("delta").mode("append").save(metadata_path)
