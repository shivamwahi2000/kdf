"""Full load ingestion skill."""

from pyspark.sql import DataFrame

from kdf.skills.base import DataSkill
from kdf.core.context import ExecutionContext


class FullLoadSkill(DataSkill):
    """Full load ingestion - reads complete dataset."""

    def execute(self, df: DataFrame, context: ExecutionContext) -> DataFrame:
        """Execute full load - simply returns the input DataFrame.

        Args:
            df: Input DataFrame
            context: Execution context

        Returns:
            Complete input DataFrame
        """
        # Full load is a pass-through - no filtering needed
        record_count = df.count()
        context.add_metric("full_load_records", record_count)

        return df
