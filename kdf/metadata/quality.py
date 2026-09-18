"""Quality results metadata store."""

from pyspark.sql import SparkSession


class QualityResultStore:
    """Store and query quality check results."""

    def __init__(self, spark: SparkSession, base_path: str = "./kdf_metadata"):
        """Initialize quality result store.

        Args:
            spark: Spark session
            base_path: Base path for metadata storage
        """
        self.spark = spark
        self.metadata_path = f"{base_path}/quality_results"

    # Quality results are currently stored in pipeline run metadata
    # This class provides a centralized interface for future enhancements
    pass
