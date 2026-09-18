"""Core pipeline execution engine."""

from typing import Optional
from pyspark.sql import DataFrame, SparkSession

from kdf.core.config import PipelineConfig
from kdf.core.context import ExecutionContext
from kdf.core.exceptions import KDFException, ValidationError
from kdf.core.models import PipelineStatus
from kdf.core.registry import connector_registry, skill_registry


class Pipeline:
    """KDF pipeline execution engine."""

    def __init__(self, config: PipelineConfig, spark: Optional[SparkSession] = None):
        """Initialize pipeline.

        Args:
            config: Pipeline configuration
            spark: Optional Spark session
        """
        self.config = config
        self.spark = spark

    def validate(self) -> None:
        """Validate pipeline configuration.

        Raises:
            ValidationError: If configuration is invalid
        """
        issues = self.config.validate_config()
        if issues:
            raise ValidationError(f"Configuration validation failed:\n" + "\n".join(f"  - {i}" for i in issues))

    def run(self, context: Optional[ExecutionContext] = None) -> ExecutionContext:
        """Execute pipeline.

        Args:
            context: Optional execution context

        Returns:
            Execution context with run results

        Raises:
            KDFException: If pipeline execution fails
        """
        # Validate configuration
        self.validate()

        # Create or use provided context
        if context is None:
            context = ExecutionContext(self.config, self.spark)

        with context:
            try:
                # Load data from source
                df = self._load_source(context)
                context.add_metric("records_read", df.count())

                # Apply ingestion skill if configured
                if self.config.ingestion:
                    df = self._apply_ingestion(df, context)

                # Apply data skills
                df = self._apply_skills(df, context)

                # Apply quality checks
                self._apply_quality_checks(df, context)

                # Write to target
                self._write_target(df, context)
                context.add_metric("records_written", df.count())

            except Exception as e:
                context.add_error(str(e))
                raise KDFException(f"Pipeline execution failed: {e}") from e

        return context

    def _load_source(self, context: ExecutionContext) -> DataFrame:
        """Load data from source."""
        source_type = self.config.source.type

        if not connector_registry.has(source_type):
            raise KDFException(f"Unknown source type: {source_type}")

        connector = connector_registry.create_connector(
            source_type,
            self.config.source.model_dump()
        )

        return connector.read(context)

    def _apply_ingestion(self, df: DataFrame, context: ExecutionContext) -> DataFrame:
        """Apply ingestion skill."""
        ingestion_skill = self.config.ingestion.skill

        if not skill_registry.has(ingestion_skill):
            raise KDFException(f"Unknown ingestion skill: {ingestion_skill}")

        skill = skill_registry.create_skill(
            ingestion_skill,
            self.config.ingestion.model_dump()
        )

        return skill.execute(df, context)

    def _apply_skills(self, df: DataFrame, context: ExecutionContext) -> DataFrame:
        """Apply data transformation skills."""
        for skill_config in self.config.skills:
            # skill_config is a dict with skill name as key
            skill_name = list(skill_config.keys())[0]
            skill_params = skill_config[skill_name]

            if not skill_registry.has(skill_name):
                raise KDFException(f"Unknown skill: {skill_name}")

            skill = skill_registry.create_skill(skill_name, skill_params)
            df = skill.execute(df, context)

        return df

    def _apply_quality_checks(self, df: DataFrame, context: ExecutionContext) -> None:
        """Apply data quality checks."""
        for check_config in self.config.quality:
            # check_config is a dict with check name as key
            check_name = list(check_config.keys())[0]
            check_params = check_config[check_name]

            if not skill_registry.has(check_name):
                raise KDFException(f"Unknown quality check: {check_name}")

            skill = skill_registry.create_skill(check_name, check_params)
            # Quality checks don't transform data, they validate it
            skill.validate(df, context)

    def _write_target(self, df: DataFrame, context: ExecutionContext) -> None:
        """Write data to target."""
        target_type = self.config.target.type

        writer = df.write.format(target_type).mode(self.config.target.mode)

        # Apply options
        for key, value in self.config.target.options.items():
            writer = writer.option(key, value)

        # Apply partitioning
        if self.config.target.partition_by:
            writer = writer.partitionBy(*self.config.target.partition_by)

        # Save
        writer.save(self.config.target.path)
