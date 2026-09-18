"""Not null data quality check."""

from typing import List
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, sum as spark_sum, when

from kdf.skills.base import QualitySkill
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import ValidationError, ConfigurationError
from kdf.core.models import QualityResult, QualityStatus


class NotNullSkill(QualitySkill):
    """Check for null values in specified columns."""

    def validate_config(self) -> None:
        """Validate not_null configuration."""
        if "columns" not in self.config:
            raise ConfigurationError("not_null requires 'columns' in configuration")

        if not isinstance(self.config["columns"], list) or not self.config["columns"]:
            raise ConfigurationError("'columns' must be a non-empty list")

    def validate(self, df: DataFrame, context: ExecutionContext) -> None:
        """Validate that specified columns have no null values.

        Args:
            df: DataFrame to validate
            context: Execution context

        Raises:
            ValidationError: If null values found
        """
        self.validate_config()

        columns: List[str] = self.config["columns"]
        total_records = df.count()

        # Check each column
        results = []
        for column in columns:
            if column not in df.columns:
                raise ValidationError(
                    f"Column '{column}' not found. Available columns: {', '.join(df.columns)}"
                )

            # Count null values
            null_count = df.filter(col(column).isNull()).count()

            status = QualityStatus.PASSED if null_count == 0 else QualityStatus.FAILED

            result = QualityResult(
                check_name="not_null",
                status=status,
                column=column,
                violations=null_count,
                total_records=total_records,
                message=f"Found {null_count} null values in column '{column}'" if null_count > 0 else f"No null values in column '{column}'",
            )
            results.append(result)

            # Store result in context
            context.add_metric(f"quality_not_null_{column}", result.model_dump())

        # Raise error if any check failed
        failed = [r for r in results if r.status == QualityStatus.FAILED]
        if failed:
            failure_summary = "\n".join([f"  - {r.column}: {r.violations} nulls" for r in failed])
            raise ValidationError(f"Not null validation failed:\n{failure_summary}")
