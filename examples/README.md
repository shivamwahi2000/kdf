# KDF Examples

This directory contains example pipeline configurations demonstrating various KDF capabilities.

## Examples Overview

### PostgreSQL Ingestion

**File**: `postgres_incremental.yaml`

Demonstrates:
- Incremental loading with watermark
- Deduplication
- Comprehensive quality checks
- Schema evolution
- Partitioned target

**Use Case**: Regularly sync orders from production PostgreSQL to data lake

**Run**:
```bash
kdf validate examples/postgres_incremental.yaml
kdf run examples/postgres_incremental.yaml
```

### S3 Parquet Load

**File**: `s3_parquet_load.yaml`

Demonstrates:
- Reading Parquet from S3
- Full load pattern
- Reconciliation
- Quality validation

**Use Case**: Daily load of transaction files from S3

**Run**:
```bash
kdf validate examples/s3_parquet_load.yaml
kdf run examples/s3_parquet_load.yaml
```

### S3 CSV Load

**File**: `s3_csv_load.yaml`

Demonstrates:
- CSV ingestion
- Schema inference
- Event data processing

**Use Case**: Load event logs from CSV files

**Run**:
```bash
kdf validate examples/s3_csv_load.yaml
kdf run examples/s3_csv_load.yaml
```

## Configuration Prerequisites

Before running examples, configure your environment:

1. **Copy environment template**
   ```bash
   cp .env.template .env
   ```

2. **Configure credentials**
   ```bash
   # PostgreSQL
   POSTGRES_HOST=your_host
   POSTGRES_DATABASE=your_db
   POSTGRES_USER=your_user
   POSTGRES_PASSWORD=your_password

   # AWS/S3
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=us-east-1
   ```

3. **Update paths**
   - Modify source paths to match your data
   - Update target paths as needed

## Customization

Each example can be customized:

### Change Source
```yaml
source:
  type: postgres
  table: your_table
  database: your_db
```

### Add Skills
```yaml
skills:
  - your_custom_skill:
      param1: value1
```

### Modify Quality Checks
```yaml
quality:
  - not_null:
      columns: [col1, col2, col3]
  - freshness:
      column: updated_at
      threshold: 12h
```

## Advanced Examples

### Incremental with Partitioned JDBC Reads

For large PostgreSQL tables, enable partitioned reads:

```yaml
source:
  type: postgres
  table: large_table
  partition_column: id
  num_partitions: 8
  lower_bound: 1
  upper_bound: 10000000
```

### Schema Evolution Modes

Choose how to handle schema changes:

```yaml
skills:
  - schema_evolution:
      mode: strict  # Block on breaking changes
```

Options:
- `compatible`: Allow additive changes
- `warning`: Warn but continue
- `strict`: Block on any breaking change

### Multiple Quality Checks

Combine various quality checks:

```yaml
quality:
  - not_null:
      columns: [id, date, amount]

  - unique:
      columns: [id]

  - freshness:
      column: updated_at
      threshold: 2h

  - reconcile:
      keys: [id]
```

## Monitoring

After running pipelines:

```bash
# View recent runs
kdf status

# Check specific pipeline history
kdf history orders_ingestion

# Query metadata
# Use Spark SQL against kdf_metadata/pipeline_runs
```

## Troubleshooting

### Connection Issues

If PostgreSQL connection fails:
- Verify credentials in `.env`
- Check network connectivity
- Ensure PostgreSQL accepts connections
- Verify SSL settings if required

If S3 access fails:
- Check AWS credentials
- Verify bucket permissions
- Ensure correct region
- Check S3 path exists

### Quality Check Failures

Quality checks intentionally fail on bad data:
- Review error messages
- Check `kdf_metadata/pipeline_runs` for details
- Fix data quality at source
- Adjust thresholds if needed

### Performance Issues

For slow pipelines:
- Enable partitioned JDBC reads (PostgreSQL)
- Increase fetch size
- Review Spark UI for bottlenecks
- Consider data volume and cluster size

## Next Steps

1. Start with a simple example
2. Customize for your use case
3. Add more skills and checks
4. Monitor in production
5. Contribute your patterns back!

## Questions?

- Check the [main README](../README.md)
- Review [documentation](../docs/)
- Open an issue on GitHub
