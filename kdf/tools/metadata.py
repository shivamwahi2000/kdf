"""Metadata inspection tools."""

from typing import List
from pyspark.sql import SparkSession

from kdf.tools.base import Tool
from kdf.core.models import ToolInput, ToolOutput
from kdf.metadata.runs import RunMetadataStore


class InspectPipelineRunTool(Tool):
    """Inspect a specific pipeline run."""

    def __init__(self, spark: SparkSession, metadata_path: str = "./kdf_metadata"):
        """Initialize tool."""
        super().__init__()
        self.store = RunMetadataStore(spark, metadata_path)

    @property
    def description(self) -> str:
        return "Inspect detailed information about a specific pipeline run by run_id"

    @property
    def input_schema(self) -> List[ToolInput]:
        return [
            ToolInput(
                name="run_id",
                description="Unique identifier for the pipeline run",
                type="string",
                required=True,
            )
        ]

    def execute(self, run_id: str) -> ToolOutput:
        """Execute tool."""
        try:
            run = self.store.get_run(run_id)

            if not run:
                return ToolOutput(
                    success=False,
                    data=None,
                    error=f"Run not found: {run_id}"
                )

            return ToolOutput(
                success=True,
                data=run.model_dump(),
                error=None
            )
        except Exception as e:
            return ToolOutput(
                success=False,
                data=None,
                error=str(e)
            )


class InspectPipelineHistoryTool(Tool):
    """Inspect pipeline execution history."""

    def __init__(self, spark: SparkSession, metadata_path: str = "./kdf_metadata"):
        """Initialize tool."""
        super().__init__()
        self.store = RunMetadataStore(spark, metadata_path)

    @property
    def description(self) -> str:
        return "Get execution history for a pipeline, including recent runs and status"

    @property
    def input_schema(self) -> List[ToolInput]:
        return [
            ToolInput(
                name="pipeline_name",
                description="Name of the pipeline",
                type="string",
                required=True,
            ),
            ToolInput(
                name="limit",
                description="Maximum number of runs to return (default: 10)",
                type="integer",
                required=False,
            ),
        ]

    def execute(self, pipeline_name: str, limit: int = 10) -> ToolOutput:
        """Execute tool."""
        try:
            runs = self.store.get_pipeline_history(pipeline_name, limit)

            return ToolOutput(
                success=True,
                data=[run.model_dump() for run in runs],
                error=None
            )
        except Exception as e:
            return ToolOutput(
                success=False,
                data=None,
                error=str(e)
            )
