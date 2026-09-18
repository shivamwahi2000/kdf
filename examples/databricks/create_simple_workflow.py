"""
Example: Create a simple single-pipeline Databricks workflow
"""

from kdf.databricks.workflow_builder import (
    WorkflowBuilder,
    ClusterConfig,
    SCHEDULE_DAILY_2AM,
)

# Create workflow builder
workflow = WorkflowBuilder(
    name="KDF Simple Pipeline",
    notebook_path="/Workspace/kdf/notebooks/run_kdf_pipeline",
    metadata_path="/kdf/metadata",
)

# Add a cluster configuration
workflow.add_cluster(
    "kdf_cluster",
    ClusterConfig(
        spark_version="13.3.x-scala2.12",
        node_type_id="i3.xlarge",
        num_workers=2,
        spark_conf={
            "spark.databricks.delta.preview.enabled": "true",
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true",
        },
        custom_tags={
            "framework": "kdf",
            "version": "0.1",
            "environment": "production",
        },
    ),
)

# Add the pipeline task
workflow.add_single_pipeline_task(
    task_key="run_orders_pipeline",
    config_path="dbfs:/kdf/configs/orders_pipeline.yaml",
    cluster_key="kdf_cluster",
    description="Ingest orders from PostgreSQL to Delta Lake",
    timeout_seconds=3600,
    max_retries=2,
)

# Set schedule (daily at 2am)
workflow.set_schedule(
    cron_expression=SCHEDULE_DAILY_2AM,
    timezone="America/Los_Angeles",
)

# Set notifications
workflow.set_email_notifications(
    on_failure=["data-engineering@company.com"],
)

# Build and save
workflow_json = workflow.build()
workflow.save("simple_workflow.json")

print("✓ Simple workflow created: simple_workflow.json")
print("\nTo deploy:")
print("  databricks jobs create --json-file simple_workflow.json")
