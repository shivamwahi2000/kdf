"""Reconciliation skill for source-target validation."""

from typing import Dict, List, Optional
from pyspark.sql import DataFrame
from pyspark.sql.functions import col

from kdf.skills.base import DataSkill
from kdf.core.context import ExecutionContext
from kdf.core.models import ReconciliationResult
from kdf.core.exceptions import ConfigurationError


class ReconciliationSkill(DataSkill):
    """Reconcile source and target data counts."""

    def execute(self, df: DataFrame, context: ExecutionContext) -> DataFrame:
        """Perform reconciliation between source and target.

        Args:
            df: Source DataFrame (what was written)
            context: Execution context

        Returns:
            Input DataFrame (unchanged)

        Configuration:
            target_path: Optional path to target data for comparison
            keys: Optional list of keys for detailed reconciliation

        Note:
            This is a validation skill that doesn't transform data.
        """
        source_count = df.count()

        # Count duplicates in source
        keys = self.config.get("keys", [])
        source_duplicates = 0
        if keys:
            source_duplicates = source_count - df.dropDuplicates(keys).count()

        # Get target count if target path provided
        target_path = self.config.get("target_path") or context.config.target.path
        target_count = 0
        target_duplicates = 0

        try:
            target_df = context.spark.read.format("delta").load(target_path)
            target_count = target_df.count()

            if keys:
                target_duplicates = target_count - target_df.dropDuplicates(keys).count()
        except Exception as e:
            # Target doesn't exist yet (first run)
            context.add_metric("reconciliation_target_not_found", str(e))

        # Calculate difference
        difference = abs(source_count - target_count)
        match_rate = None
        if target_count > 0:
            match_rate = (min(source_count, target_count) / max(source_count, target_count)) * 100

        # Create result
        result = ReconciliationResult(
            source_records=source_count,
            target_records=target_count,
            difference=difference,
            source_duplicates=source_duplicates,
            target_duplicates=target_duplicates,
            match_rate=match_rate,
        )

        # Store in context
        context.add_metric("reconciliation_result", result.model_dump())

        # Log summary
        context.add_metric("reconciliation_source_records", source_count)
        context.add_metric("reconciliation_target_records", target_count)
        context.add_metric("reconciliation_difference", difference)

        return df
