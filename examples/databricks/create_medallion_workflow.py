"""
Example: Create a Databricks workflow from a KDF medallion config
"""

from kdf.core.config import MedallionPipelineConfig
from kdf.databricks.workflow_builder import (
    create_medallion_workflow_from_config,
    ClusterConfig,
    SCHEDULE_DAILY_2AM,
)
import json

# Load medallion config
config = MedallionPipelineConfig.from_yaml("../medallion_orders.yaml")

print(f"Creating workflow for: {config.name}")
print(f"Pipelines: {len(config.pipelines)}")

# Create custom cluster configuration
cluster_config = ClusterConfig(
    spark_version="13.3.x-scala2.12",
    node_type_id="i3.xlarge",
    num_workers=4,
    spark_conf={
        "spark.databricks.delta.preview.enabled": "true",
        "spark.databricks.delta.optimizeWrite.enabled": "true",
        "spark.databricks.delta.autoCompact.enabled": "true",
        "spark.sql.adaptive.enabled": "true",
        "spark.sql.adaptive.coalescePartitions.enabled": "true",
    },
    custom_tags={
        "framework": "kdf",
        "version": "0.1",
        "architecture": "medallion",
        "environment": "production",
    },
)

# Create workflow automatically from config
workflow_json = create_medallion_workflow_from_config(
    medallion_config=config,
    workflow_name="Orders Medallion Pipeline",
    config_path="dbfs:/kdf/configs/medallion_orders.yaml",
    cluster_config=cluster_config,
    schedule_cron=SCHEDULE_DAILY_2AM,
    notification_emails=["data-engineering@company.com"],
)

# Save workflow JSON
with open("medallion_workflow.json", "w") as f:
    json.dump(workflow_json, f, indent=2)

print("\n✓ Medallion workflow created: medallion_workflow.json")
print(f"\nWorkflow includes {len(workflow_json['tasks'])} tasks:")
for task in workflow_json["tasks"]:
    print(f"  - {task['task_key']}: {task['description']}")

print("\nTo deploy:")
print("  databricks jobs create --json-file medallion_workflow.json")
