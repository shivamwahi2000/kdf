"""Freshness data quality check."""

import re
from datetime import datetime, timedelta
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, max as spark_max

from kdf.skills.base import QualitySkill
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import ValidationError, ConfigurationError
from kdf.core.models import QualityResult, QualityStatus


class FreshnessSkill(QualitySkill):
    """Check data freshness based on timestamp column."""

    def validate_config(self) -> None:
        """Validate freshness configuration."""
        if "column" not in self.config:
            raise ConfigurationError("freshness requires 'column' in configuration")
        if "threshold" not in self.config:
            raise ConfigurationError("freshness requires 'threshold' in configuration")

    def validate(self, df: DataFrame, context: ExecutionContext) -> None:
        """Validate data freshness.

        Args:
            df: DataFrame to validate
            context: Execution context

        Configuration:
            column: Timestamp column to check
            threshold: Maximum age (e.g., "6h", "24h", "7d")

        Raises:
            ValidationError: If data is stale
        """
        self.validate_config()

        column = self.config["column"]
        threshold_str = self.config["threshold"]

        # Validate column exists
        if column not in df.columns:
            raise ValidationError(
                f"Column '{column}' not found. Available columns: {', '.join(df.columns)}"
            )

        # Parse threshold
        threshold_seconds = self._parse_threshold(threshold_str)
        threshold_delta = timedelta(seconds=threshold_seconds)

        # Get max timestamp from data
        max_timestamp = df.agg(spark_max(col(column))).collect()[0][0]

        if max_timestamp is None:
            raise ValidationError(f"Column '{column}' has no non-null values")

        # Calculate age
        now = datetime.utcnow()
        if hasattr(max_timestamp, "to_pydatetime"):
            max_timestamp = max_timestamp.to_pydatetime()

        age = now - max_timestamp
        is_fresh = age <= threshold_delta

        status = QualityStatus.PASSED if is_fresh else QualityStatus.FAILED

        result = QualityResult(
            check_name="freshness",
            status=status,
            column=column,
            violations=0 if is_fresh else 1,
            total_records=1,
            message=f"Data age: {self._format_timedelta(age)} (threshold: {threshold_str})",
            metadata={
                "max_timestamp": str(max_timestamp),
                "age_seconds": age.total_seconds(),
                "threshold_seconds": threshold_seconds,
            }
        )

        # Store result in context
        context.add_metric(f"quality_freshness_{column}", result.model_dump())

        if status == QualityStatus.FAILED:
            raise ValidationError(
                f"Data freshness check failed: {result.message}. "
                f"Last update: {max_timestamp}"
            )

    def _parse_threshold(self, threshold: str) -> int:
        """Parse threshold string to seconds.

        Args:
            threshold: String like "6h", "24h", "7d"

        Returns:
            Seconds as integer
        """
        match = re.match(r"^(\d+)(s|m|h|d)$", threshold.lower())
        if not match:
            raise ConfigurationError(
                f"Invalid threshold format: {threshold}. "
                "Use format like '6h', '24h', '7d' (s=seconds, m=minutes, h=hours, d=days)"
            )

        value = int(match.group(1))
        unit = match.group(2)

        multipliers = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
        }

        return value * multipliers[unit]

    def _format_timedelta(self, td: timedelta) -> str:
        """Format timedelta for human reading.

        Args:
            td: Timedelta

        Returns:
            Formatted string
        """
        total_seconds = int(td.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            return f"{total_seconds // 60}m"
        elif total_seconds < 86400:
            return f"{total_seconds // 3600}h"
        else:
            return f"{total_seconds // 86400}d"
