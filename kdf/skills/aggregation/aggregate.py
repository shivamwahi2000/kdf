"""Aggregation skill for creating Gold layer metrics."""

from typing import List, Dict, Any
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    sum as spark_sum, count, avg, min as spark_min, max as spark_max,
    countDistinct, col
)

from kdf.skills.base import DataSkill
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import SkillExecutionError, ConfigurationError


class AggregateSkill(DataSkill):
    """Aggregate data for Gold layer metrics and summaries."""

    def validate_config(self) -> None:
        """Validate aggregation configuration."""
        if "group_by" not in self.config:
            raise ConfigurationError("Aggregation requires 'group_by' in configuration")

        if "metrics" not in self.config or not self.config["metrics"]:
            raise ConfigurationError("Aggregation requires 'metrics' in configuration")

    def execute(self, df: DataFrame, context: ExecutionContext) -> DataFrame:
        """Execute aggregation.

        Args:
            df: Input DataFrame
            context: Execution context

        Returns:
            Aggregated DataFrame

        Configuration:
            group_by: List of column names to group by
            metrics: List of metric definitions
                Each metric is a dict with:
                - name: Output column name
                - agg: Aggregation function (sum, count, avg, min, max, count_distinct)
                - column: Source column (not needed for count)

        Example:
            aggregate:
              group_by: [order_date, customer_id]
              metrics:
                - name: total_revenue
                  agg: sum
                  column: amount
                - name: order_count
                  agg: count
                - name: avg_order_value
                  agg: avg
                  column: amount
        """
        self.validate_config()

        group_by_cols: List[str] = self.config["group_by"]
        metrics: List[Dict[str, Any]] = self.config["metrics"]

        # Validate group_by columns exist
        missing_cols = [c for c in group_by_cols if c not in df.columns]
        if missing_cols:
            raise SkillExecutionError(
                f"Group by columns not found: {', '.join(missing_cols)}. "
                f"Available columns: {', '.join(df.columns)}"
            )

        input_count = df.count()
        context.add_metric("aggregate_input_records", input_count)

        # Start grouping
        grouped = df.groupBy(*group_by_cols)

        # Build aggregation expressions
        agg_exprs = []
        for metric in metrics:
            metric_name = metric.get("name")
            agg_func = metric.get("agg")
            source_col = metric.get("column")

            if not metric_name:
                raise ConfigurationError("Each metric must have a 'name'")

            if not agg_func:
                raise ConfigurationError(f"Metric '{metric_name}' must specify 'agg' function")

            # Build expression based on aggregation type
            if agg_func == "count":
                expr = count("*").alias(metric_name)
            elif agg_func == "count_distinct":
                if not source_col:
                    raise ConfigurationError(f"Metric '{metric_name}' with count_distinct requires 'column'")
                if source_col not in df.columns:
                    raise SkillExecutionError(f"Column '{source_col}' not found")
                expr = countDistinct(col(source_col)).alias(metric_name)
            elif agg_func == "sum":
                if not source_col:
                    raise ConfigurationError(f"Metric '{metric_name}' with sum requires 'column'")
                if source_col not in df.columns:
                    raise SkillExecutionError(f"Column '{source_col}' not found")
                expr = spark_sum(col(source_col)).alias(metric_name)
            elif agg_func == "avg":
                if not source_col:
                    raise ConfigurationError(f"Metric '{metric_name}' with avg requires 'column'")
                if source_col not in df.columns:
                    raise SkillExecutionError(f"Column '{source_col}' not found")
                expr = avg(col(source_col)).alias(metric_name)
            elif agg_func == "min":
                if not source_col:
                    raise ConfigurationError(f"Metric '{metric_name}' with min requires 'column'")
                if source_col not in df.columns:
                    raise SkillExecutionError(f"Column '{source_col}' not found")
                expr = spark_min(col(source_col)).alias(metric_name)
            elif agg_func == "max":
                if not source_col:
                    raise ConfigurationError(f"Metric '{metric_name}' with max requires 'column'")
                if source_col not in df.columns:
                    raise SkillExecutionError(f"Column '{source_col}' not found")
                expr = spark_max(col(source_col)).alias(metric_name)
            else:
                raise ConfigurationError(
                    f"Unknown aggregation function: {agg_func}. "
                    f"Supported: sum, count, avg, min, max, count_distinct"
                )

            agg_exprs.append(expr)

        # Perform aggregation
        aggregated_df = grouped.agg(*agg_exprs)

        output_count = aggregated_df.count()
        context.add_metric("aggregate_output_records", output_count)
        context.add_metric("aggregate_reduction_ratio", round(input_count / output_count if output_count > 0 else 0, 2))

        return aggregated_df
