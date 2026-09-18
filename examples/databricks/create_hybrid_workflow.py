"""
Example: Create a hybrid batch + streaming Databricks workflow
"""

from kdf.databricks.workflow_builder import (
    WorkflowBuilder,
    ClusterConfig,
    DEFAULT_BATCH_CLUSTER,
    DEFAULT_STREAMING_CLUSTER,
    SCHEDULE_HOURLY,
)

# Create workflow builder
workflow = WorkflowBuilder(
    name="KDF Hybrid Pipeline - Batch + Streaming",
    notebook_path="/Workspace/kdf/notebooks/run_kdf_pipeline",
    metadata_path="/kdf/metadata",
)

# Add batch cluster
workflow.add_cluster("batch_cluster", DEFAULT_BATCH_CLUSTER)

# Add streaming cluster with autoscaling
streaming_cluster = ClusterConfig(
    spark_version="13.3.x-scala2.12",
    node_type_id="i3.xlarge",
    autoscale_min_workers=2,
    autoscale_max_workers=8,
    spark_conf={
        "spark.databricks.delta.preview.enabled": "true",
        "spark.streaming.backpressure.enabled": "true",
        "spark.streaming.kafka.maxRatePerPartition": "1000",
        "spark.sql.streaming.stateStore.maintenanceInterval": "300s",
    },
    custom_tags={
        "framework": "kdf",
        "cluster_type": "streaming",
        "autoscale": "true",
    },
)
workflow.add_cluster("streaming_cluster", streaming_cluster)

# Bronze layer - Batch historical data
workflow.add_medallion_pipeline_task(
    task_key="bronze_orders_batch",
    config_path="dbfs:/kdf/configs/hybrid_clickstream.yaml",
    pipeline_name="bronze_orders_batch",
    cluster_key="batch_cluster",
    description="Bronze batch - Historical orders from PostgreSQL",
)

# Bronze layer - Streaming real-time data
workflow.add_medallion_pipeline_task(
    task_key="bronze_clickstream_streaming",
    config_path="dbfs:/kdf/configs/hybrid_clickstream.yaml",
    pipeline_name="bronze_clickstream_streaming",
    cluster_key="streaming_cluster",
    description="Bronze streaming - Real-time clickstream from Kafka",
    timeout_seconds=0,  # No timeout for streaming
    max_retries=0,
)

# Silver layer - Batch path
workflow.add_medallion_pipeline_task(
    task_key="silver_orders",
    config_path="dbfs:/kdf/configs/hybrid_clickstream.yaml",
    pipeline_name="silver_orders",
    cluster_key="batch_cluster",
    description="Silver batch - Clean batch orders",
    depends_on=["bronze_orders_batch"],
)

# Silver layer - Streaming path
workflow.add_medallion_pipeline_task(
    task_key="silver_clickstream",
    config_path="dbfs:/kdf/configs/hybrid_clickstream.yaml",
    pipeline_name="silver_clickstream",
    cluster_key="streaming_cluster",
    description="Silver streaming - Process streaming clickstream",
    depends_on=["bronze_clickstream_streaming"],
    timeout_seconds=0,  # No timeout for streaming
    max_retries=0,
)

# Gold layer - Combined analytics
workflow.add_medallion_pipeline_task(
    task_key="gold_user_activity",
    config_path="dbfs:/kdf/configs/hybrid_clickstream.yaml",
    pipeline_name="gold_user_activity",
    cluster_key="batch_cluster",
    description="Gold layer - Combined analytics from batch and streaming",
    depends_on=["silver_orders", "silver_clickstream"],
)

# Set schedule (hourly for batch components)
workflow.set_schedule(
    cron_expression=SCHEDULE_HOURLY,
    timezone="UTC",
)

# Set notifications
workflow.set_email_notifications(
    on_failure=["data-engineering@company.com"],
)

# Set workflow configuration
workflow.set_timeout(14400)  # 4 hours
workflow.set_concurrency(1)

# Build and save
workflow_json = workflow.build()
workflow.save("hybrid_workflow.json")

print("✓ Hybrid workflow created: hybrid_workflow.json")
print("\nWorkflow structure:")
print("  Batch Path:")
print("    → bronze_orders_batch")
print("    → silver_orders")
print("\n  Streaming Path:")
print("    → bronze_clickstream_streaming")
print("    → silver_clickstream")
print("\n  Combined:")
print("    → gold_user_activity")

print("\nClusters:")
print("  - batch_cluster: i3.xlarge x4 workers")
print("  - streaming_cluster: i3.xlarge x2-8 autoscale")

print("\nTo deploy:")
print("  databricks jobs create --json-file hybrid_workflow.json")
