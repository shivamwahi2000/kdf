"""Schema inspection tools."""

from typing import List
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

from kdf.tools.base import Tool
from kdf.core.models import ToolInput, ToolOutput


class InspectSchemaTool(Tool):
    """Inspect schema of a dataset."""

    def __init__(self, spark: SparkSession):
        """Initialize tool."""
        super().__init__()
        self.spark = spark

    @property
    def description(self) -> str:
        return "Inspect the schema of a Delta table or dataset"

    @property
    def input_schema(self) -> List[ToolInput]:
        return [
            ToolInput(
                name="path",
                description="Path to Delta table or dataset",
                type="string",
                required=True,
            )
        ]

    def execute(self, path: str) -> ToolOutput:
        """Execute tool."""
        try:
            df = self.spark.read.format("delta").load(path)
            schema = df.schema

            return ToolOutput(
                success=True,
                data={
                    "path": path,
                    "columns": [
                        {
                            "name": field.name,
                            "type": str(field.dataType),
                            "nullable": field.nullable,
                        }
                        for field in schema.fields
                    ],
                },
                error=None
            )
        except Exception as e:
            return ToolOutput(
                success=False,
                data=None,
                error=str(e)
            )


class CompareSchemaTool(Tool):
    """Compare schemas between two datasets."""

    def __init__(self, spark: SparkSession):
        """Initialize tool."""
        super().__init__()
        self.spark = spark

    @property
    def description(self) -> str:
        return "Compare schemas between two datasets and identify differences"

    @property
    def input_schema(self) -> List[ToolInput]:
        return [
            ToolInput(
                name="path1",
                description="Path to first dataset",
                type="string",
                required=True,
            ),
            ToolInput(
                name="path2",
                description="Path to second dataset",
                type="string",
                required=True,
            ),
        ]

    def execute(self, path1: str, path2: str) -> ToolOutput:
        """Execute tool."""
        try:
            df1 = self.spark.read.format("delta").load(path1)
            df2 = self.spark.read.format("delta").load(path2)

            schema1 = {f.name: f for f in df1.schema.fields}
            schema2 = {f.name: f for f in df2.schema.fields}

            # Find differences
            only_in_1 = [name for name in schema1 if name not in schema2]
            only_in_2 = [name for name in schema2 if name not in schema1]
            type_differences = []

            for name in schema1:
                if name in schema2:
                    type1 = str(schema1[name].dataType)
                    type2 = str(schema2[name].dataType)
                    if type1 != type2:
                        type_differences.append({
                            "column": name,
                            "type1": type1,
                            "type2": type2,
                        })

            return ToolOutput(
                success=True,
                data={
                    "path1": path1,
                    "path2": path2,
                    "only_in_first": only_in_1,
                    "only_in_second": only_in_2,
                    "type_differences": type_differences,
                    "identical": len(only_in_1) == 0 and len(only_in_2) == 0 and len(type_differences) == 0,
                },
                error=None
            )
        except Exception as e:
            return ToolOutput(
                success=False,
                data=None,
                error=str(e)
            )
