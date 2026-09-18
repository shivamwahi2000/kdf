"""Schema evolution detection skill."""

from datetime import datetime
from typing import Dict, List, Optional
from pyspark.sql import DataFrame
from pyspark.sql.types import StructType

from kdf.skills.base import DataSkill
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import SchemaError
from kdf.core.models import SchemaChange, SchemaChangeType


class SchemaEvolutionSkill(DataSkill):
    """Detect and handle schema changes."""

    def execute(self, df: DataFrame, context: ExecutionContext) -> DataFrame:
        """Detect schema changes.

        Args:
            df: Input DataFrame
            context: Execution context

        Returns:
            Input DataFrame (unchanged)

        Configuration:
            mode: "compatible", "warning", or "strict" (default: "compatible")
                  - compatible: Allow additive changes
                  - warning: Warn on any changes but continue
                  - strict: Block on any breaking changes

        Raises:
            SchemaError: If breaking changes detected in strict mode
        """
        mode = self.config.get("mode", "compatible")
        current_schema = df.schema

        # Get last known schema
        last_schema = self._get_last_schema(context)

        if last_schema is None:
            # First run - save schema
            self._save_schema(context, current_schema)
            context.add_metric("schema_evolution_first_run", True)
            return df

        # Detect changes
        changes = self._detect_changes(last_schema, current_schema)

        if not changes:
            context.add_metric("schema_evolution_no_changes", True)
            return df

        # Classify changes
        breaking_changes = [c for c in changes if c.change_type == SchemaChangeType.BREAKING]
        warnings = [c for c in changes if c.change_type == SchemaChangeType.WARNING]
        compatible = [c for c in changes if c.change_type == SchemaChangeType.COMPATIBLE]

        context.add_metric("schema_evolution_changes", len(changes))
        context.add_metric("schema_evolution_breaking", len(breaking_changes))
        context.add_metric("schema_evolution_warnings", len(warnings))
        context.add_metric("schema_evolution_compatible", len(compatible))

        # Handle based on mode
        if mode == "strict" and breaking_changes:
            self._raise_breaking_error(breaking_changes)
        elif mode == "warning" and changes:
            # Log warnings but continue
            for change in changes:
                context.add_metric(f"schema_warning_{change.column_name}", change.description)

        # Save new schema
        self._save_schema(context, current_schema)

        return df

    def _get_last_schema(self, context: ExecutionContext) -> Optional[StructType]:
        """Get last known schema from metadata."""
        try:
            from pyspark.sql.types import StructType as SparkStructType
            from pyspark.sql.functions import col

            metadata_path = f"{context.metadata_path}/schemas"
            schemas_df = context.spark.read.format("delta").load(metadata_path)

            result = (
                schemas_df
                .filter(col("pipeline_name") == context.config.name)
                .orderBy(col("recorded_at").desc())
                .limit(1)
                .collect()
            )

            if result:
                # Reconstruct schema from JSON
                schema_json = result[0]["schema_json"]
                return SparkStructType.fromJson(eval(schema_json))
            return None
        except Exception:
            # Metadata table doesn't exist yet
            return None

    def _save_schema(self, context: ExecutionContext, schema: StructType) -> None:
        """Save schema to metadata."""
        from pyspark.sql.types import StructType as SparkStructType, StructField, StringType, TimestampType

        metadata_path = f"{context.metadata_path}/schemas"

        schema_data = [(
            context.config.name,
            str(schema.jsonValue()),
            datetime.utcnow()
        )]

        metadata_schema = SparkStructType([
            StructField("pipeline_name", StringType(), False),
            StructField("schema_json", StringType(), False),
            StructField("recorded_at", TimestampType(), False),
        ])

        schema_df = context.spark.createDataFrame(schema_data, metadata_schema)
        schema_df.write.format("delta").mode("append").save(metadata_path)

    def _detect_changes(self, old_schema: StructType, new_schema: StructType) -> List[SchemaChange]:
        """Detect changes between schemas."""
        changes = []

        old_fields = {f.name: f for f in old_schema.fields}
        new_fields = {f.name: f for f in new_schema.fields}

        # Check for removed columns
        for col_name in old_fields:
            if col_name not in new_fields:
                changes.append(SchemaChange(
                    column_name=col_name,
                    change_type=SchemaChangeType.BREAKING,
                    old_type=str(old_fields[col_name].dataType),
                    new_type=None,
                    description=f"Column '{col_name}' was removed"
                ))

        # Check for new columns
        for col_name in new_fields:
            if col_name not in old_fields:
                changes.append(SchemaChange(
                    column_name=col_name,
                    change_type=SchemaChangeType.COMPATIBLE,
                    old_type=None,
                    new_type=str(new_fields[col_name].dataType),
                    description=f"Column '{col_name}' was added"
                ))

        # Check for type changes
        for col_name in old_fields:
            if col_name in new_fields:
                old_type = str(old_fields[col_name].dataType)
                new_type = str(new_fields[col_name].dataType)

                if old_type != new_type:
                    changes.append(SchemaChange(
                        column_name=col_name,
                        change_type=SchemaChangeType.BREAKING,
                        old_type=old_type,
                        new_type=new_type,
                        description=f"Column '{col_name}' type changed from {old_type} to {new_type}"
                    ))

        return changes

    def _raise_breaking_error(self, breaking_changes: List[SchemaChange]) -> None:
        """Raise error for breaking changes."""
        error_msg = "BREAKING SCHEMA CHANGES DETECTED:\n\n"

        for change in breaking_changes:
            error_msg += f"Column: {change.column_name}\n"
            if change.old_type and change.new_type:
                error_msg += f"  Expected: {change.old_type}\n"
                error_msg += f"  Received: {change.new_type}\n"
            else:
                error_msg += f"  {change.description}\n"
            error_msg += "\n"

        error_msg += "Pipeline execution blocked. Review schema changes before proceeding."

        raise SchemaError(error_msg)
