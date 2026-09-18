"""SQL query tools."""

from typing import List
from pyspark.sql import SparkSession

from kdf.tools.base import Tool
from kdf.core.models import ToolInput, ToolOutput


class QueryMetadataTool(Tool):
    """Query metadata using SQL."""

    def __init__(self, spark: SparkSession, metadata_path: str = "./kdf_metadata"):
        """Initialize tool."""
        super().__init__()
        self.spark = spark
        self.metadata_path = metadata_path

    @property
    def description(self) -> str:
        return "Execute SQL queries against KDF metadata tables (pipeline_runs, watermarks, schemas)"

    @property
    def input_schema(self) -> List[ToolInput]:
        return [
            ToolInput(
                name="query",
                description="SQL query to execute",
                type="string",
                required=True,
            ),
            ToolInput(
                name="limit",
                description="Maximum rows to return (default: 100)",
                type="integer",
                required=False,
            ),
        ]

    def execute(self, query: str, limit: int = 100) -> ToolOutput:
        """Execute tool."""
        try:
            # Register metadata tables as temp views
            try:
                runs_df = self.spark.read.format("delta").load(f"{self.metadata_path}/pipeline_runs")
                runs_df.createOrReplaceTempView("kdf_pipeline_runs")
            except Exception:
                pass

            try:
                watermarks_df = self.spark.read.format("delta").load(f"{self.metadata_path}/watermarks")
                watermarks_df.createOrReplaceTempView("kdf_watermarks")
            except Exception:
                pass

            try:
                schemas_df = self.spark.read.format("delta").load(f"{self.metadata_path}/schemas")
                schemas_df.createOrReplaceTempView("kdf_schemas")
            except Exception:
                pass

            # Execute query
            result_df = self.spark.sql(query).limit(limit)
            results = [row.asDict() for row in result_df.collect()]

            return ToolOutput(
                success=True,
                data={
                    "rows": results,
                    "count": len(results),
                    "schema": [{"name": f.name, "type": str(f.dataType)} for f in result_df.schema.fields],
                },
                error=None
            )
        except Exception as e:
            return ToolOutput(
                success=False,
                data=None,
                error=str(e)
            )
