"""Watermark metadata store."""

from typing import Optional
from pyspark.sql import SparkSession


class WatermarkStore:
    """Store and query watermarks."""

    def __init__(self, spark: SparkSession, base_path: str = "./kdf_metadata"):
        """Initialize watermark store.

        Args:
            spark: Spark session
            base_path: Base path for metadata storage
        """
        self.spark = spark
        self.metadata_path = f"{base_path}/watermarks"

    # Watermark operations are handled directly by IncrementalLoadSkill
    # This class provides a centralized interface for future enhancements
    pass
