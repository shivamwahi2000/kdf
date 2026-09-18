# KDF Quick Start Guide

## Installation

```bash
cd /path/to/kdf
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```

## Verify Installation

```bash
kdf --version
kdf connector list
kdf skill list
```

Expected output:
```
Registered connectors:
  - postgres
  - s3

Registered skills:
  - deduplicate
  - freshness
  - full_load
  - incremental
  - not_null
  - reconcile
  - schema_evolution
  - unique
```

## First Pipeline

### 1. Initialize Project

```bash
mkdir my_pipeline
cd my_pipeline
kdf init
```

This creates:
- `pipeline.yaml` - Example configuration
- `.env.template` - Credentials template

### 2. Configure Credentials

```bash
cp .env.template .env
# Edit .env with your actual credentials
```

### 3. Create Pipeline Configuration

Edit `pipeline.yaml`:

```yaml
name: my_first_pipeline

source:
  type: postgres
  connection: my_postgres
  database: mydb
  schema: public
  table: orders

ingestion:
  skill: full_load

target:
  type: delta
  path: /data/orders
```

### 4. Validate

```bash
kdf validate pipeline.yaml
```

### 5. Run

```bash
kdf run pipeline.yaml
```

### 6. Check Results

```bash
kdf status
kdf history my_first_pipeline
```

## Environment Variables

Required for PostgreSQL:
```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=mydb
POSTGRES_USER=user
POSTGRES_PASSWORD=password
```

Required for S3:
```bash
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_REGION=us-east-1
```

## Common Pipeline Patterns

### Incremental Load

```yaml
ingestion:
  skill: incremental
  column: updated_at
```

### With Deduplication

```yaml
skills:
  - deduplicate:
      keys: [id]
      order_by: updated_at
```

### With Quality Checks

```yaml
quality:
  - not_null:
      columns: [id, name, date]
  - unique:
      columns: [id]
  - freshness:
      column: updated_at
      threshold: 6h
```

## CLI Commands

```bash
# Project setup
kdf init                          # Initialize project

# Pipeline operations
kdf validate pipeline.yaml        # Validate configuration
kdf run pipeline.yaml             # Execute pipeline

# Monitoring
kdf status                        # Show recent runs
kdf history PIPELINE_NAME         # Pipeline history

# Discovery
kdf connector list                # List connectors
kdf skill list                    # List skills
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# With coverage
pytest --cov=kdf
```

## Example Pipelines

Try the included examples:

```bash
# PostgreSQL incremental load
kdf validate examples/postgres_incremental.yaml
kdf run examples/postgres_incremental.yaml

# S3 parquet load
kdf validate examples/s3_parquet_load.yaml
kdf run examples/s3_parquet_load.yaml

# S3 CSV load
kdf validate examples/s3_csv_load.yaml
kdf run examples/s3_csv_load.yaml
```

## Troubleshooting

### Import Errors

If you get import errors:
```bash
pip install -e .
```

### Connection Errors

Check:
1. Credentials in `.env`
2. Network connectivity
3. Firewall rules
4. Service availability

### Quality Check Failures

Quality checks fail on purpose when data doesn't meet criteria. This is expected behavior. Review:
1. Error message
2. Metadata in `kdf_metadata/`
3. Source data quality

## Next Steps

1. **Read the README**: Complete feature overview
2. **Review Examples**: `examples/` directory
3. **Check Documentation**: `docs/` directory
4. **Try Agent Skills**: `kdf/agents/skills/*/SKILL.md`
5. **Contribute**: See `CONTRIBUTING.md`

## Getting Help

- **Documentation**: Check `README.md` and `docs/`
- **Examples**: See `examples/` directory
- **Issues**: Report on GitHub
- **Implementation Details**: See `IMPLEMENTATION_SUMMARY.md`

## Architecture Overview

```
Your Pipeline YAML
       ↓
    KDF Core
       ↓
   Connectors (PostgreSQL, S3)
       ↓
   Data Skills (Ingestion, Quality, Transform)
       ↓
   Databricks/Spark Runtime
       ↓
   Delta Lake Target
       ↓
   Metadata (Queryable)
```

## Key Concepts

- **Connector**: Reads from data sources
- **Skill**: Reusable data operation
- **Pipeline**: Orchestrates connectors and skills
- **Context**: Runtime state and metrics
- **Metadata**: Delta-backed execution history
- **Tools**: Agent-friendly inspection capabilities

## Quick Tips

1. **Start Simple**: Begin with a basic full load
2. **Add Incrementally**: Add skills one at a time
3. **Monitor Metadata**: Use `kdf_metadata/` for debugging
4. **Validate First**: Always `kdf validate` before `kdf run`
5. **Use Examples**: Copy and modify existing examples

---

**Ready to build? Start with `kdf init`**
