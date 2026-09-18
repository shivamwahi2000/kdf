"""Deduplication skill."""

from typing import List
from pyspark.sql import DataFrame, Window
from pyspark.sql.functions import col, row_number, desc

from kdf.skills.base import DataSkill
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import SkillExecutionError, ConfigurationError


class DeduplicateSkill(DataSkill):
    """Deduplicate records based on key columns."""

    def validate_config(self) -> None:
        """Validate deduplication configuration."""
        if "keys" not in self.config:
            raise ConfigurationError("Deduplication requires 'keys' in configuration")

        if not isinstance(self.config["keys"], list) or not self.config["keys"]:
            raise ConfigurationError("'keys' must be a non-empty list")

    def execute(self, df: DataFrame, context: ExecutionContext) -> DataFrame:
        """Execute deduplication.

        Args:
            df: Input DataFrame
            context: Execution context

        Returns:
            Deduplicated DataFrame

        Configuration:
            keys: List of column names to use as deduplication keys
            order_by: Optional column to determine which duplicate to keep (keeps max value)

        Example:
            deduplicate:
              keys: [order_id]
              order_by: updated_at
        """
        self.validate_config()

        keys: List[str] = self.config["keys"]
        order_by: str = self.config.get("order_by")

        # Validate key columns exist
        missing_cols = [k for k in keys if k not in df.columns]
        if missing_cols:
            raise SkillExecutionError(
                f"Key columns not found: {', '.join(missing_cols)}. "
                f"Available columns: {', '.join(df.columns)}"
            )

        if order_by and order_by not in df.columns:
            raise SkillExecutionError(
                f"Order column '{order_by}' not found. "
                f"Available columns: {', '.join(df.columns)}"
            )

        # Count input records
        input_count = df.count()
        context.add_metric("dedup_input_records", input_count)

        if order_by:
            # Use window function to keep the record with max order_by value
            window = Window.partitionBy(*keys).orderBy(desc(order_by))
            deduplicated_df = (
                df.withColumn("_row_num", row_number().over(window))
                .filter(col("_row_num") == 1)
                .drop("_row_num")
            )
        else:
            # Simple deduplication - keep first occurrence
            deduplicated_df = df.dropDuplicates(keys)

        # Count output records
        output_count = deduplicated_df.count()
        duplicates = input_count - output_count

        context.add_metric("dedup_output_records", output_count)
        context.add_metric("dedup_duplicates_removed", duplicates)

        if duplicates > 0:
            duplicate_rate = (duplicates / input_count) * 100
            context.add_metric("dedup_duplicate_rate_percent", round(duplicate_rate, 2))

        return deduplicated_df
