"""Base skill interfaces."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from pyspark.sql import DataFrame

from kdf.core.context import ExecutionContext
from kdf.core.models import SkillMetrics


class DataSkill(ABC):
    """Base class for data transformation skills."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize skill.

        Args:
            config: Skill configuration
        """
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    def execute(self, df: DataFrame, context: ExecutionContext) -> DataFrame:
        """Execute skill transformation.

        Args:
            df: Input DataFrame
            context: Execution context

        Returns:
            Transformed DataFrame

        Raises:
            SkillExecutionError: If execution fails
        """
        pass

    def validate_config(self) -> None:
        """Validate skill configuration.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass

    def metrics(self, input_df: DataFrame, output_df: DataFrame, duration: float) -> SkillMetrics:
        """Generate skill metrics.

        Args:
            input_df: Input DataFrame
            output_df: Output DataFrame
            duration: Execution duration in seconds

        Returns:
            Skill metrics
        """
        return SkillMetrics(
            skill_name=self.name,
            input_records=input_df.count() if input_df else 0,
            output_records=output_df.count() if output_df else 0,
            duration_seconds=duration,
        )


class QualitySkill(ABC):
    """Base class for data quality skills."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize quality skill.

        Args:
            config: Skill configuration
        """
        self.config = config
        self.name = self.__class__.__name__

    @abstractmethod
    def validate(self, df: DataFrame, context: ExecutionContext) -> None:
        """Validate data quality.

        Args:
            df: DataFrame to validate
            context: Execution context

        Raises:
            ValidationError: If quality check fails
        """
        pass

    def validate_config(self) -> None:
        """Validate skill configuration.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        pass
