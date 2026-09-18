# Agent Skill: Databricks Workflow Creator

## Purpose
Create and deploy Databricks Workflows for KDF pipelines automatically. This skill enables AI agents to translate KDF pipeline configurations into production-ready Databricks Workflows with proper task dependencies, cluster configurations, and schedules.

## When to Use
- User requests deployment to Databricks
- Converting KDF pipelines to scheduled workflows
- Setting up production orchestration for medallion architectures
- Creating hybrid batch/streaming workflows in Databricks

## Capabilities

### 1. Single Pipeline Workflows
Create workflows for standalone KDF pipelines with:
- Single task configuration
- Cluster sizing
- Schedule configuration
- Retry policies
- Email notifications

### 2. Medallion Workflows
Create multi-task workflows from medallion configs with:
- Automatic task dependency graph (Bronze → Silver → Gold)
- Layer-specific descriptions
- Proper execution order
- Parallel execution where possible

### 3. Hybrid Workflows
Create workflows mixing batch and streaming:
- Separate clusters for batch vs streaming
- Different timeout/retry policies
- Combined analytics tasks

### 4. Full Deployment
Handle end-to-end deployment:
- Upload config files to DBFS
- Build and upload KDF wheel
- Upload runner notebook to workspace
- Create workflow via Databricks Jobs API
- Validate workflow creation

## Available Tools

### Python API

#### `WorkflowBuilder`
Programmatic workflow creation:

```python
from kdf.databricks.workflow_builder import (
    WorkflowBuilder,
    ClusterConfig,
    SCHEDULE_DAILY_2AM,
)

workflow = WorkflowBuilder(
    name="My KDF Pipeline",
    notebook_path="/Workspace/kdf/notebooks/run_kdf_pipeline",
    metadata_path="/kdf/metadata"
)

workflow.add_cluster("main_cluster", ClusterConfig(num_workers=4))
workflow.add_single_pipeline_task(
    task_key="run_pipeline",
    config_path="dbfs:/kdf/configs/my_pipeline.yaml",
    cluster_key="main_cluster"
)
workflow.set_schedule(SCHEDULE_DAILY_2AM)
workflow.save("workflow.json")
```

#### `create_medallion_workflow_from_config`
Automatic workflow creation from medallion config:

```python
from kdf.databricks.workflow_builder import create_medallion_workflow_from_config
from kdf.core.config import MedallionPipelineConfig

config = MedallionPipelineConfig.from_yaml("medallion.yaml")
workflow = create_medallion_workflow_from_config(
    medallion_config=config,
    workflow_name="Orders Medallion",
    config_path="dbfs:/kdf/configs/medallion.yaml",
    schedule_cron="0 0 2 * * ?",
    notification_emails=["team@company.com"]
)
```

### CLI Commands

#### Upload Config
```bash
kdf databricks upload-config my_pipeline.yaml --dbfs-path /kdf/configs
```

#### Create Workflow
```bash
kdf databricks create-workflow medallion.yaml \
  --config-path dbfs:/kdf/configs/medallion.yaml \
  --schedule "0 0 2 * * ?" \
  --notification-emails team@company.com
```

#### Upload Notebook
```bash
kdf databricks upload-notebook --workspace-path /Workspace/kdf/notebooks
```

#### Upload KDF Wheel
```bash
kdf databricks upload-kdf --dbfs-path /kdf/wheels
```

#### Complete Deployment
```bash
kdf databricks deploy medallion.yaml \
  --schedule "0 0 2 * * ?" \
  --notification-emails team@company.com
```

## Decision Tree

### Step 1: Identify Config Type
```
Read KDF config file
  → Has "pipelines" list? → Medallion workflow
  → Has "source" and "target"? → Single pipeline workflow
  → Otherwise → ERROR
```

### Step 2: Determine Execution Pattern
```
For each pipeline:
  → execution_mode == "batch"? → Use batch cluster, normal timeout
  → execution_mode == "streaming"? → Use streaming cluster, no timeout
  → execution_mode == "micro_batch"? → Use streaming cluster, normal timeout
```

### Step 3: Choose Cluster Configuration
```
Batch workload:
  → Small data (<100GB): 2-4 workers, i3.xlarge
  → Medium data (100GB-1TB): 4-8 workers, i3.xlarge
  → Large data (>1TB): 8-16 workers, i3.2xlarge

Streaming workload:
  → Low throughput (<10k msgs/sec): 2-4 workers, autoscale
  → High throughput (>10k msgs/sec): 4-8 workers, autoscale
```

### Step 4: Set Schedule
```
Bronze layer:
  → Streaming source → No schedule (always running)
  → Batch source → Hourly or based on source update frequency

Silver layer:
  → Depends on Bronze → Same or slightly delayed

Gold layer:
  → Business metrics → Daily (typically 2am)
  → Operational metrics → Hourly or based on SLA
```

### Step 5: Configure Notifications
```
Always set on_failure notifications
Consider on_success for critical pipelines
Never set for streaming (too noisy)
```

## Example Agent Workflow

### Scenario: User requests Databricks deployment

```
User: "Deploy my medallion pipeline to Databricks"

Agent Actions:

1. ANALYZE CONFIG
   - Read pipeline config file
   - Identify as medallion (has 3 pipelines: bronze, silver, gold)
   - Check execution modes (all batch)

2. DETERMINE REQUIREMENTS
   - Batch workload → Standard cluster config
   - Bronze source is PostgreSQL → Hourly schedule appropriate
   - 3 layers → Need dependency graph

3. CREATE WORKFLOW
   ```python
   from kdf.databricks.workflow_builder import create_medallion_workflow_from_config
   from kdf.core.config import MedallionPipelineConfig

   config = MedallionPipelineConfig.from_yaml("orders_medallion.yaml")
   workflow = create_medallion_workflow_from_config(
       medallion_config=config,
       workflow_name="Orders Medallion Pipeline",
       config_path="dbfs:/kdf/configs/orders_medallion.yaml",
       schedule_cron="0 0 * * * ?",  # Hourly
       notification_emails=["team@company.com"]
   )

   import json
   with open("workflow.json", "w") as f:
       json.dump(workflow, f, indent=2)
   ```

4. EXPLAIN TO USER
   "Created Databricks workflow with:
   - 3 tasks: bronze_orders → silver_orders → gold_daily_revenue
   - Cluster: i3.xlarge with 4 workers
   - Schedule: Hourly
   - Notifications: team@company.com on failure

   Next steps:
   1. Upload config: kdf databricks upload-config orders_medallion.yaml
   2. Create workflow: databricks jobs create --json-file workflow.json
   3. Trigger first run: databricks jobs run-now --job-id <ID>"

5. PROVIDE MONITORING
   "Monitor workflow at:
   https://<workspace>.databricks.com/#job/<job_id>

   Check pipeline metadata:
   SELECT * FROM delta.`/kdf/metadata/pipeline_runs`
   WHERE pipeline_name = 'bronze_orders'
   ORDER BY start_time DESC"
```

## Cluster Configuration Reference

### Predefined Configs

```python
from kdf.databricks.workflow_builder import (
    DEFAULT_BATCH_CLUSTER,      # 4 workers, batch optimized
    DEFAULT_STREAMING_CLUSTER,  # 2-8 autoscale, streaming optimized
)
```

### Custom Config Template

```python
ClusterConfig(
    spark_version="13.3.x-scala2.12",
    node_type_id="i3.xlarge",
    num_workers=4,  # OR autoscale_min/max_workers
    spark_conf={
        "spark.databricks.delta.preview.enabled": "true",
        "spark.databricks.delta.optimizeWrite.enabled": "true",
        "spark.sql.adaptive.enabled": "true",
    },
    custom_tags={
        "framework": "kdf",
        "environment": "production",
    }
)
```

## Schedule Templates

```python
from kdf.databricks.workflow_builder import (
    SCHEDULE_HOURLY,        # "0 0 * * * ?"
    SCHEDULE_DAILY_2AM,     # "0 0 2 * * ?"
    SCHEDULE_EVERY_15MIN,   # "0 */15 * * * ?"
    SCHEDULE_EVERY_5MIN,    # "0 */5 * * * ?"
)
```

## Common Patterns

### Pattern 1: Simple Daily Batch
```python
workflow = WorkflowBuilder(name="Daily Orders")
workflow.add_cluster("batch", ClusterConfig(num_workers=4))
workflow.add_single_pipeline_task(
    task_key="ingest_orders",
    config_path="dbfs:/kdf/configs/orders.yaml",
    cluster_key="batch"
)
workflow.set_schedule(SCHEDULE_DAILY_2AM)
```

### Pattern 2: Medallion with Dependencies
```python
config = MedallionPipelineConfig.from_yaml("medallion.yaml")
workflow = create_medallion_workflow_from_config(
    medallion_config=config,
    config_path="dbfs:/kdf/configs/medallion.yaml",
    schedule_cron=SCHEDULE_HOURLY
)
# Automatically creates Bronze → Silver → Gold with dependencies
```

### Pattern 3: Hybrid Batch + Streaming
```python
workflow = WorkflowBuilder(name="Hybrid Pipeline")
workflow.add_cluster("batch", DEFAULT_BATCH_CLUSTER)
workflow.add_cluster("streaming", DEFAULT_STREAMING_CLUSTER)

# Batch path
workflow.add_medallion_pipeline_task(
    task_key="bronze_batch",
    config_path="dbfs:/kdf/configs/hybrid.yaml",
    pipeline_name="bronze_orders_batch",
    cluster_key="batch"
)

# Streaming path
workflow.add_medallion_pipeline_task(
    task_key="bronze_stream",
    config_path="dbfs:/kdf/configs/hybrid.yaml",
    pipeline_name="bronze_clickstream_streaming",
    cluster_key="streaming",
    timeout_seconds=0  # No timeout for streaming
)

# Combined analytics
workflow.add_medallion_pipeline_task(
    task_key="gold_combined",
    config_path="dbfs:/kdf/configs/hybrid.yaml",
    pipeline_name="gold_user_activity",
    cluster_key="batch",
    depends_on=["bronze_batch", "bronze_stream"]
)
```

## Error Handling

### Common Errors

1. **Config Not Found**
   ```
   Error: Config file not found: pipeline.yaml
   Solution: Verify file path, check current directory
   ```

2. **Databricks CLI Not Configured**
   ```
   Error: Databricks CLI not found
   Solution: pip install databricks-cli && databricks configure --token
   ```

3. **Circular Dependencies**
   ```
   Error: Circular dependency detected among pipelines: [A, B, C]
   Solution: Review depends_on in config, remove cycle
   ```

4. **Invalid Cron Expression**
   ```
   Error: Invalid cron expression
   Solution: Use Quartz format: "0 0 2 * * ?" (sec min hour day month dow)
   ```

## Best Practices

1. **Start Simple**: Begin with single-pipeline workflow, expand to medallion
2. **Use Templates**: Leverage predefined cluster configs and schedules
3. **Test Locally**: Validate config with `kdf validate` before deploying
4. **Monitor Metadata**: Query `/kdf/metadata/pipeline_runs` for health checks
5. **Incremental Deployment**: Deploy Bronze first, then Silver, then Gold
6. **Separate Clusters**: Use different clusters for batch vs streaming
7. **Set Timeouts**: Always set reasonable timeouts (except for streaming)
8. **Enable Notifications**: Always set failure notifications
9. **Tag Resources**: Use custom_tags for cost tracking and organization
10. **Document Workflows**: Include descriptions in tasks and workflows

## Output Format

When creating workflows, always provide:

1. **Workflow Summary**
   - Name
   - Number of tasks
   - Execution order/dependencies
   - Cluster configurations
   - Schedule

2. **Deployment Instructions**
   - Commands to upload config
   - Commands to create workflow
   - Commands to trigger test run

3. **Monitoring Information**
   - Databricks workflow URL
   - Metadata query examples
   - Key metrics to watch

4. **Next Steps**
   - How to monitor
   - How to troubleshoot
   - How to update

## Related Skills
- pipeline_builder: Create KDF configs that will be deployed
- pipeline_debugger: Troubleshoot workflow failures
- data_quality_investigator: Analyze quality issues in workflows

## Success Criteria
- Workflow JSON is valid
- Dependencies are correct
- Cluster configuration is appropriate for workload
- Schedule matches business requirements
- Notifications are configured
- Deployment instructions are clear
