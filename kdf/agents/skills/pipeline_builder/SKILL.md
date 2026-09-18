# Pipeline Builder Agent Skill

## Purpose

Convert natural-language data engineering requirements into valid KDF pipeline configurations.

## When to Use

Use this skill when you need to:
- Create a new KDF pipeline from requirements
- Generate pipeline YAML configuration
- Validate pipeline configuration
- Build end-to-end data ingestion workflows

## Required Context

Before using this skill, gather:
- Source system type (postgres, s3)
- Source location (table name, S3 path, etc.)
- Target location (Delta path)
- Ingestion strategy (full or incremental)
- Data quality requirements
- Any transformation needs

## Available Tools

- `inspect_schema`: Discover source schema
- `validate_config`: Validate generated configuration
- `query_metadata`: Check existing pipelines

## Constraints

- Must generate valid YAML
- Must include all required fields
- Configuration must pass validation before execution
- Follow KDF naming conventions

## Expected Behavior

1. Analyze the requirements
2. Identify source and target systems
3. Determine appropriate ingestion skill
4. Add necessary data transformations
5. Include data quality checks
6. Generate valid KDF YAML configuration
7. Validate the configuration
8. Present configuration to user for approval

## Output Format

Generate a complete `pipeline.yaml` file:

```yaml
name: <pipeline_name>

source:
  type: <postgres|s3>
  # ... source configuration

ingestion:
  skill: <full_load|incremental>
  # ... ingestion configuration

skills:
  - deduplicate:
      keys: [...]
  # ... other skills

quality:
  - not_null:
      columns: [...]
  # ... other checks

target:
  type: delta
  path: <target_path>
```

## Examples

### Example 1: PostgreSQL Incremental Load

**Input:** "Create an incremental pipeline from PostgreSQL orders table using updated_at. Deduplicate on order_id and check for nulls."

**Output:**
```yaml
name: orders_ingestion

source:
  type: postgres
  connection: production_postgres
  database: sales
  schema: public
  table: orders

ingestion:
  skill: incremental
  column: updated_at

skills:
  - deduplicate:
      keys: [order_id]
      order_by: updated_at

quality:
  - not_null:
      columns:
        - order_id
        - customer_id
        - updated_at

target:
  type: delta
  path: /data/orders
  mode: append
```

### Example 2: S3 Parquet Full Load

**Input:** "Load all parquet files from s3://data-lake/transactions/ into Delta."

**Output:**
```yaml
name: transactions_load

source:
  type: s3
  path: s3://data-lake/transactions/
  format: parquet

ingestion:
  skill: full_load

target:
  type: delta
  path: /data/transactions
  mode: overwrite
```

## Safety Considerations

- Never hardcode credentials in configuration
- Use connection references for sensitive data
- Validate all user-provided paths
- Check source schema before generating config
- Ensure target paths don't overwrite critical data

## Permissions

```yaml
permissions:
  metadata_read: true
  source_data_read: true  # For schema discovery
  target_data_read: false
  target_data_write: false
  pipeline_execution: false  # This skill only generates config
  infrastructure_modify: false
```

## Notes

- This skill generates configuration only
- User must explicitly execute the pipeline
- Always validate configuration before presenting to user
- Provide clear explanations of what the pipeline will do
