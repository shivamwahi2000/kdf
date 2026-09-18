"""Unique data quality check."""

from typing import List
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, count

from kdf.skills.base import QualitySkill
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import ValidationError, ConfigurationError
from kdf.core.models import QualityResult, QualityStatus


class UniqueSkill(QualitySkill):
    """Check for duplicate values in specified columns."""

    def validate_config(self) -> None:
        """Validate unique configuration."""
        if "columns" not in self.config:
            raise ConfigurationError("unique requires 'columns' in configuration")

        if not isinstance(self.config["columns"], list) or not self.config["columns"]:
            raise ConfigurationError("'columns' must be a non-empty list")

    def validate(self, df: DataFrame, context: ExecutionContext) -> None:
        """Validate that specified column combinations are unique.

        Args:
            df: DataFrame to validate
            context: Execution context

        Raises:
            ValidationError: If duplicate values found
        """
        self.validate_config()

        columns: List[str] = self.config["columns"]

        # Validate columns exist
        missing_cols = [c for c in columns if c not in df.columns]
        if missing_cols:
            raise ValidationError(
                f"Columns not found: {', '.join(missing_cols)}. "
                f"Available columns: {', '.join(df.columns)}"
            )

        total_records = df.count()

        # Count duplicates
        duplicate_counts = (
            df.groupBy(*columns)
            .agg(count("*").alias("count"))
            .filter(col("count") > 1)
        )

        duplicate_groups = duplicate_counts.count()
        total_duplicates = duplicate_counts.agg({"count": "sum"}).collect()[0][0] if duplicate_groups > 0 else 0

        # Adjust for counting: if we have n identical records, we have n-1 duplicates
        violations = total_duplicates - duplicate_groups if duplicate_groups > 0 else 0

        status = QualityStatus.PASSED if violations == 0 else QualityStatus.FAILED

        column_str = ", ".join(columns)
        result = QualityResult(
            check_name="unique",
            status=status,
            column=column_str,
            violations=violations,
            total_records=total_records,
            message=f"Found {violations} duplicate records for columns [{column_str}]" if violations > 0 else f"All records unique for columns [{column_str}]",
            metadata={"duplicate_groups": duplicate_groups}
        )

        # Store result in context
        context.add_metric(f"quality_unique_{'_'.join(columns)}", result.model_dump())

        if status == QualityStatus.FAILED:
            raise ValidationError(result.message)
