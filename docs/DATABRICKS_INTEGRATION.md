# KDF Databricks Integration Guide

## Overview

KDF integrates seamlessly with Databricks Workflows to provide production-grade orchestration for your data pipelines. This guide covers everything from initial setup to advanced deployment patterns.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Setup](#setup)
4. [Deployment Patterns](#deployment-patterns)
5. [CLI Reference](#cli-reference)
6. [Python API](#python-api)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Prerequisites

### Required

- Databricks workspace (AWS, Azure, or GCP)
- Databricks CLI configured with access token
- KDF installed (`pip install kdf`)
- Python 3.8+

### Recommended

- Understanding of KDF pipeline configs
- Familiarity with Databricks Workflows
- Access to Databricks workspace with job creation permissions

---

## Quick Start

### 1. Install Databricks CLI

```bash
pip install databricks-cli
```

### 2. Configure Databricks CLI

```bash
databricks configure --token
```

Enter your workspace URL and access token when prompted.

### 3. Deploy Your First Pipeline

```bash
# Upload your config
kdf databricks upload-config my_pipeline.yaml

# Create workflow
kdf databricks create-workflow my_pipeline.yaml \
  --config-path dbfs:/kdf/configs/my_pipeline.yaml \
  --schedule "0 0 2 * * ?"

# Or use the convenience command
kdf databricks deploy my_pipeline.yaml --schedule "0 0 2 * * ?"
```

### 4. Monitor Execution

Visit your Databricks workspace → Workflows → Find your job

---

## Setup

### Step 1: Upload KDF to Databricks

Build and upload the KDF wheel file:

```bash
kdf databricks upload-kdf --dbfs-path /kdf/wheels
```

This creates `/kdf/wheels/kdf-0.1.0-py3-none-any.whl` in DBFS.

### Step 2: Upload Runner Notebook

Upload the KDF pipeline runner notebook:

```bash
kdf databricks upload-notebook --workspace-path /Workspace/kdf/notebooks
```

This uploads the notebook to `/Workspace/kdf/notebooks/run_kdf_pipeline`.

### Step 3: Configure Cluster Libraries (Optional)

If you want KDF pre-installed on your cluster:

1. Go to Databricks workspace → Compute
2. Select your cluster → Libraries
3. Install new library → DBFS → `/kdf/wheels/kdf-0.1.0-py3-none-any.whl`

Alternatively, the notebook installs KDF automatically if not present.

---

## Deployment Patterns

### Pattern 1: Single Pipeline Workflow

**Use Case**: Simple daily batch ingestion

**KDF Config** (`orders_pipeline.yaml`):
```yaml
name: orders_pipeline
source:
  type: postgres
  connection: production_db
  table: orders
ingestion:
  skill: incremental
  column: updated_at
target:
  type: delta
  path: /data/orders
```

**Deploy**:
```bash
kdf databricks deploy orders_pipeline.yaml \
  --schedule "0 0 2 * * ?" \
  --notification-emails team@company.com
```

**Result**:
- Single-task workflow
- Runs daily at 2am
- Email notifications on failure

---

### Pattern 2: Medallion Workflow

**Use Case**: Multi-layer data architecture with dependencies

**KDF Config** (`medallion_orders.yaml`):
```yaml
name: orders_medallion
pipelines:
  - name: bronze_orders
    medallion:
      layer: bronze
    source: { type: postgres, table: orders }
    target: { path: /medallion/bronze/orders }

  - name: silver_orders
    depends_on: [bronze_orders]
    medallion:
      layer: silver
    source: { type: delta, path: /medallion/bronze/orders }
    skills: [deduplicate, schema_evolution]
    target: { path: /medallion/silver/orders }

  - name: gold_revenue
    depends_on: [silver_orders]
    medallion:
      layer: gold
    source: { type: delta, path: /medallion/silver/orders }
    skills:
      - aggregate:
          group_by: [date]
          metrics:
            - { name: revenue, agg: sum, column: amount }
    target: { path: /medallion/gold/revenue }
```

**Deploy**:
```bash
kdf databricks deploy medallion_orders.yaml \
  --schedule "0 0 2 * * ?" \
  --notification-emails team@company.com
```

**Result**:
- 3-task workflow with dependencies
- Bronze → Silver → Gold execution order
- Automatic dependency management
- Single cluster for all tasks

**Workflow Structure**:
```
Stage 1: bronze_orders
    ↓
Stage 2: silver_orders
    ↓
Stage 3: gold_revenue
```

---

### Pattern 3: Hybrid Batch + Streaming

**Use Case**: Combine historical batch data with real-time streaming

**KDF Config** (`hybrid_pipeline.yaml`):
```yaml
name: hybrid_pipeline
pipelines:
  # Batch path
  - name: bronze_batch
    execution_mode: batch
    source: { type: postgres, table: orders }
    target: { path: /bronze/batch }

  # Streaming path
  - name: bronze_stream
    execution_mode: streaming
    trigger: "5 minutes"
    checkpoint_location: /checkpoints/bronze
    source:
      type: kafka
      bootstrap_servers: kafka:9092
      topic: clickstream
    target: { path: /bronze/stream }

  # Combined analytics
  - name: gold_combined
    depends_on: [bronze_batch, bronze_stream]
    source: { type: delta, path: /bronze }
    skills: [aggregate]
    target: { path: /gold/metrics }
```

**Deploy with Python** (for advanced control):

```python
from kdf.databricks.workflow_builder import (
    WorkflowBuilder,
    DEFAULT_BATCH_CLUSTER,
    DEFAULT_STREAMING_CLUSTER,
)

workflow = WorkflowBuilder(name="Hybrid Pipeline")

# Add clusters
workflow.add_cluster("batch", DEFAULT_BATCH_CLUSTER)
workflow.add_cluster("streaming", DEFAULT_STREAMING_CLUSTER)

# Batch task
workflow.add_medallion_pipeline_task(
    task_key="bronze_batch",
    config_path="dbfs:/kdf/configs/hybrid_pipeline.yaml",
    pipeline_name="bronze_batch",
    cluster_key="batch"
)

# Streaming task (no timeout, no retries)
workflow.add_medallion_pipeline_task(
    task_key="bronze_stream",
    config_path="dbfs:/kdf/configs/hybrid_pipeline.yaml",
    pipeline_name="bronze_stream",
    cluster_key="streaming",
    timeout_seconds=0,
    max_retries=0
)

# Analytics task
workflow.add_medallion_pipeline_task(
    task_key="gold_combined",
    config_path="dbfs:/kdf/configs/hybrid_pipeline.yaml",
    pipeline_name="gold_combined",
    cluster_key="batch",
    depends_on=["bronze_batch", "bronze_stream"]
)

workflow.set_schedule("0 0 * * * ?")  # Hourly
workflow.save("hybrid_workflow.json")
```

**Deploy**:
```bash
# Upload config
kdf databricks upload-config hybrid_pipeline.yaml

# Create workflow from JSON
databricks jobs create --json-file hybrid_workflow.json
```

---

## CLI Reference

### `kdf databricks upload-config`

Upload KDF config to DBFS.

```bash
kdf databricks upload-config CONFIG_FILE [OPTIONS]
```

**Options**:
- `--dbfs-path`: DBFS destination path (default: `/kdf/configs`)
- `--overwrite`: Overwrite if exists

**Example**:
```bash
kdf databricks upload-config my_pipeline.yaml \
  --dbfs-path /kdf/configs \
  --overwrite
```

---

### `kdf databricks create-workflow`

Create Databricks workflow from KDF config.

```bash
kdf databricks create-workflow CONFIG_FILE [OPTIONS]
```

**Options**:
- `--workflow-name`: Workflow name (defaults to config name)
- `--config-path`: DBFS path to config (e.g., `dbfs:/kdf/configs/pipeline.yaml`)
- `--schedule`: Cron schedule (e.g., `"0 0 2 * * ?"`)
- `--notification-emails`: Comma-separated emails
- `--output`: Save to file instead of creating in Databricks

**Examples**:

```bash
# Create workflow in Databricks
kdf databricks create-workflow medallion.yaml \
  --config-path dbfs:/kdf/configs/medallion.yaml \
  --schedule "0 0 2 * * ?" \
  --notification-emails team@company.com

# Generate JSON without creating
kdf databricks create-workflow medallion.yaml \
  --output workflow.json
```

---

### `kdf databricks upload-notebook`

Upload KDF runner notebook to workspace.

```bash
kdf databricks upload-notebook [OPTIONS]
```

**Options**:
- `--notebook-path`: Local path to notebook (default: `kdf/databricks/notebooks/run_kdf_pipeline.py`)
- `--workspace-path`: Workspace destination (default: `/Workspace/kdf/notebooks`)

**Example**:
```bash
kdf databricks upload-notebook \
  --workspace-path /Workspace/kdf/notebooks
```

---

### `kdf databricks upload-kdf`

Build and upload KDF wheel to DBFS.

```bash
kdf databricks upload-kdf [OPTIONS]
```

**Options**:
- `--dbfs-path`: DBFS destination path (default: `/kdf/wheels`)

**Example**:
```bash
kdf databricks upload-kdf --dbfs-path /kdf/wheels
```

---

### `kdf databricks deploy`

Complete deployment: upload config and create workflow.

```bash
kdf databricks deploy CONFIG_FILE [OPTIONS]
```

**Options**:
- `--workflow-name`: Workflow name
- `--schedule`: Cron schedule
- `--notification-emails`: Comma-separated emails

**Example**:
```bash
kdf databricks deploy medallion.yaml \
  --schedule "0 0 2 * * ?" \
  --notification-emails team@company.com
```

---

## Python API

### WorkflowBuilder

Create workflows programmatically.

```python
from kdf.databricks.workflow_builder import (
    WorkflowBuilder,
    ClusterConfig,
    SCHEDULE_DAILY_2AM,
)

# Create builder
workflow = WorkflowBuilder(
    name="My KDF Pipeline",
    notebook_path="/Workspace/kdf/notebooks/run_kdf_pipeline",
    metadata_path="/kdf/metadata"
)

# Add cluster
workflow.add_cluster(
    "main_cluster",
    ClusterConfig(
        num_workers=4,
        spark_conf={
            "spark.databricks.delta.preview.enabled": "true",
            "spark.sql.adaptive.enabled": "true",
        }
    )
)

# Add task
workflow.add_single_pipeline_task(
    task_key="run_pipeline",
    config_path="dbfs:/kdf/configs/my_pipeline.yaml",
    cluster_key="main_cluster",
    description="Ingest orders"
)

# Set schedule
workflow.set_schedule(SCHEDULE_DAILY_2AM)

# Set notifications
workflow.set_email_notifications(
    on_failure=["team@company.com"]
)

# Build and save
workflow.save("workflow.json")
```

---

### create_medallion_workflow_from_config

Automatic workflow creation from medallion config.

```python
from kdf.databricks.workflow_builder import create_medallion_workflow_from_config
from kdf.core.config import MedallionPipelineConfig

# Load config
config = MedallionPipelineConfig.from_yaml("medallion.yaml")

# Create workflow
workflow = create_medallion_workflow_from_config(
    medallion_config=config,
    workflow_name="Orders Medallion",
    config_path="dbfs:/kdf/configs/medallion.yaml",
    schedule_cron="0 0 2 * * ?",
    notification_emails=["team@company.com"]
)

# Save
import json
with open("workflow.json", "w") as f:
    json.dump(workflow, f, indent=2)
```

---

## Monitoring

### Databricks UI

1. Navigate to Workflows
2. Find your workflow
3. View run history, logs, and metrics

**Direct URL**:
```
https://<workspace>.databricks.com/#job/<job_id>
```

---

### KDF Metadata

Query pipeline run metadata:

```sql
-- Recent runs
SELECT
  pipeline_name,
  run_id,
  status,
  start_time,
  end_time,
  records_read,
  records_written
FROM delta.`/kdf/metadata/pipeline_runs`
ORDER BY start_time DESC
LIMIT 10;

-- Failure analysis
SELECT
  pipeline_name,
  COUNT(*) as failure_count,
  MAX(start_time) as last_failure
FROM delta.`/kdf/metadata/pipeline_runs`
WHERE status = 'FAILED'
GROUP BY pipeline_name
ORDER BY failure_count DESC;

-- Performance trends
SELECT
  DATE(start_time) as run_date,
  pipeline_name,
  AVG(UNIX_TIMESTAMP(end_time) - UNIX_TIMESTAMP(start_time)) as avg_duration_seconds,
  AVG(records_written) as avg_records
FROM delta.`/kdf/metadata/pipeline_runs`
WHERE status = 'SUCCESS'
GROUP BY DATE(start_time), pipeline_name
ORDER BY run_date DESC;
```

---

### Alerts

Set up alerts in Databricks:

1. Workflows → Select workflow → Alerts
2. Add alert condition (e.g., failure rate > 10%)
3. Configure notification (email, Slack, PagerDuty)

---

## Troubleshooting

### Problem: Notebook not found

**Error**:
```
Error: Notebook not found at /Workspace/kdf/notebooks/run_kdf_pipeline
```

**Solution**:
```bash
kdf databricks upload-notebook
```

---

### Problem: KDF not installed

**Error** (in notebook output):
```
ERROR: KDF not found. Please install KDF wheel file first.
```

**Solution**:
```bash
# Upload KDF wheel
kdf databricks upload-kdf

# Notebook will auto-install from /kdf/wheels/kdf-*.whl
```

---

### Problem: Config file not found

**Error**:
```
ERROR: Config file not found at dbfs:/kdf/configs/my_pipeline.yaml
```

**Solution**:
```bash
# Upload config
kdf databricks upload-config my_pipeline.yaml
```

---

### Problem: Workflow creation fails

**Error**:
```
Error: Request failed with status code 400
```

**Solution**:
1. Validate JSON: `cat workflow.json | jq .`
2. Check workflow name uniqueness
3. Verify cluster configuration
4. Validate cron expression

---

### Problem: Task fails with timeout

**Error**:
```
Task exceeded timeout of 3600 seconds
```

**Solution**:
- Increase timeout in workflow config
- Optimize pipeline (add partitioning, tune Spark config)
- Consider breaking into smaller tasks

---

## Best Practices

### 1. Start Simple

Begin with a single pipeline, then expand:

```bash
# Week 1: Bronze layer
kdf databricks deploy bronze.yaml

# Week 2: Add Silver
kdf databricks deploy bronze_silver.yaml

# Week 3: Complete medallion
kdf databricks deploy medallion.yaml
```

---

### 2. Use Appropriate Cluster Sizes

**Small data (<100GB)**:
- 2-4 workers, i3.xlarge
- Cost: ~$2-4/hour

**Medium data (100GB-1TB)**:
- 4-8 workers, i3.xlarge
- Cost: ~$4-8/hour

**Large data (>1TB)**:
- 8-16 workers, i3.2xlarge
- Cost: ~$16-32/hour

**Streaming**:
- Autoscale 2-8 workers
- Use backpressure
- Monitor lag

---

### 3. Set Reasonable Schedules

```python
# Bronze (raw ingestion)
SCHEDULE_HOURLY        # For frequently updated sources

# Silver (cleaning)
SCHEDULE_HOURLY        # Same as Bronze or slightly delayed

# Gold (aggregations)
SCHEDULE_DAILY_2AM     # Business metrics, daily is often enough
```

---

### 4. Configure Notifications

```python
# Always for failures
workflow.set_email_notifications(
    on_failure=["oncall@company.com"]
)

# Critical pipelines only
workflow.set_email_notifications(
    on_failure=["oncall@company.com"],
    on_success=["team@company.com"]  # For SLA-critical pipelines
)
```

---

### 5. Monitor Metadata

Create a monitoring dashboard:

```sql
-- Success rate by pipeline (last 7 days)
CREATE OR REPLACE VIEW pipeline_health AS
SELECT
  pipeline_name,
  COUNT(*) as total_runs,
  SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_runs,
  (SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as success_rate
FROM delta.`/kdf/metadata/pipeline_runs`
WHERE start_time >= DATE_SUB(CURRENT_DATE(), 7)
GROUP BY pipeline_name;
```

---

### 6. Use Tags for Cost Tracking

```python
ClusterConfig(
    custom_tags={
        "framework": "kdf",
        "environment": "production",
        "team": "data-engineering",
        "cost_center": "analytics"
    }
)
```

---

### 7. Test Before Production

```bash
# 1. Validate locally
kdf validate my_pipeline.yaml

# 2. Test in dev environment
kdf databricks deploy my_pipeline.yaml \
  --workflow-name "DEV - My Pipeline"

# 3. Monitor first few runs

# 4. Deploy to production
kdf databricks deploy my_pipeline.yaml \
  --workflow-name "PROD - My Pipeline" \
  --notification-emails oncall@company.com
```

---

### 8. Version Control Workflows

```bash
# Store workflow JSON in git
kdf databricks create-workflow my_pipeline.yaml --output workflow.json
git add workflow.json
git commit -m "Add Databricks workflow for my_pipeline"
```

---

## Cron Schedule Reference

```
Format: second minute hour day month day_of_week

Examples:
  "0 0 2 * * ?"      # Daily at 2am
  "0 0 * * * ?"      # Every hour
  "0 */15 * * * ?"   # Every 15 minutes
  "0 0 0 * * MON"    # Every Monday at midnight
  "0 0 9-17 * * ?"   # Every hour from 9am to 5pm
```

---

## Examples

Complete examples available in:
- `examples/databricks/create_simple_workflow.py`
- `examples/databricks/create_medallion_workflow.py`
- `examples/databricks/create_hybrid_workflow.py`

---

## Summary

KDF + Databricks Workflows provides:

✅ **Zero-ops orchestration** - No Airflow to maintain
✅ **Native integration** - Databricks-optimized execution
✅ **Auto-scaling** - Cost-efficient cluster management
✅ **Agent-friendly** - Programmatic workflow creation
✅ **Medallion support** - Built-in dependency management
✅ **Hybrid execution** - Mix batch and streaming
✅ **Full observability** - Metadata + Databricks monitoring

**Start deploying today:**

```bash
kdf databricks deploy your_pipeline.yaml
```

---

## Next Steps

1. Set up Databricks CLI: [Databricks CLI Guide](https://docs.databricks.com/dev-tools/cli/index.html)
2. Upload KDF: `kdf databricks upload-kdf`
3. Deploy your first pipeline: `kdf databricks deploy pipeline.yaml`
4. Monitor execution in Databricks UI
5. Query metadata for insights

For questions or issues: [KDF GitHub Issues](https://github.com/krianno/kdf/issues)
