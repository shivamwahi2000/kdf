"""S3 authentication handling."""

import os
from typing import Optional


class S3Auth:
    """S3 authentication manager."""

    @staticmethod
    def from_env() -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Load credentials from environment variables.

        Returns:
            (access_key, secret_key, region) tuple
        """
        access_key = os.getenv("AWS_ACCESS_KEY_ID")
        secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region = os.getenv("AWS_REGION", os.getenv("AWS_DEFAULT_REGION"))
        return access_key, secret_key, region

    @staticmethod
    def configure_spark(spark_session, access_key: Optional[str], secret_key: Optional[str]):
        """Configure Spark session with S3 credentials.

        Args:
            spark_session: Spark session
            access_key: AWS access key
            secret_key: AWS secret key
        """
        if access_key and secret_key:
            hadoop_conf = spark_session.sparkContext._jsc.hadoopConfiguration()
            hadoop_conf.set("fs.s3a.access.key", access_key)
            hadoop_conf.set("fs.s3a.secret.key", secret_key)
            hadoop_conf.set("fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")

    @staticmethod
    def from_instance_profile(spark_session):
        """Configure Spark to use IAM instance profile.

        Args:
            spark_session: Spark session

        Note:
            This is the recommended approach for production on AWS/Databricks.
        """
        hadoop_conf = spark_session.sparkContext._jsc.hadoopConfiguration()
        hadoop_conf.set("fs.s3a.aws.credentials.provider",
                       "com.amazonaws.auth.InstanceProfileCredentialsProvider")
