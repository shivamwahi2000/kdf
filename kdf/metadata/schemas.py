"""Schema metadata store."""

from pyspark.sql import SparkSession


class SchemaStore:
    """Store and query schema history."""

    def __init__(self, spark: SparkSession, base_path: str = "./kdf_metadata"):
        """Initialize schema store.

        Args:
            spark: Spark session
            base_path: Base path for metadata storage
        """
        self.spark = spark
        self.metadata_path = f"{base_path}/schemas"

    # Schema operations are handled directly by SchemaEvolutionSkill
    # This class provides a centralized interface for future enhancements
    pass
