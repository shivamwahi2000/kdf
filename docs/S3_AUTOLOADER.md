# S3 Autoloader - Modern Cloud File Ingestion

## Overview

KDF's S3 connector now uses **Databricks Autoloader (cloudFiles)** by default for intelligent, incremental file ingestion from cloud storage.

## What is Autoloader?

Autoloader is Databricks' modern solution for ingesting data from cloud object storage. It automatically detects and processes new files as they arrive, providing:

- **Incremental processing** - Only new files are processed
- **Schema inference** - Automatic detection of data structure
- **Schema evolution** - Handles changes in file structure
- **Efficient file discovery** - Uses cloud provider APIs
- **Rescue data** - Captures malformed records
- **Near-instant processing** - With cloud notifications

---

## Why Autoloader?

### ❌ Old Approach (Standard Spark Read)

```python
# Every run reads ALL files
df = spark.read.format("csv").load("s3://bucket/path/")
```

**Problems**:
- Reads all files every time (slow, expensive)
- No automatic schema evolution
- Manual checkpoint management
- Inefficient file listing
- No handling of malformed data

### ✅ New Approach (Autoloader)

```python
# Only reads NEW files
df = (spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "csv")
    .option("cloudFiles.schemaLocation", "/checkpoints/schema")
    .load("s3://bucket/path/")
)
```

**Benefits**:
- ✅ Only processes new files (incremental)
- ✅ Automatic schema inference and evolution
- ✅ Built-in checkpoint management
- ✅ Efficient cloud file listing
- ✅ Rescue column for bad data
- ✅ Optional near-instant processing with notifications

---

## KDF S3 Configuration

### Basic Configuration (Autoloader Enabled by Default)

```yaml
source:
  type: s3
  path: s3://my-bucket/data/orders/
  format: csv
  # use_autoloader: true  # Default is true!
```

That's it! KDF automatically uses Autoloader for streaming/incremental scenarios.

### Advanced Autoloader Configuration

```yaml
source:
  type: s3
  path: s3://my-bucket/data/orders/
  format: csv

  # Autoloader settings
  use_autoloader: true  # Explicitly enable (default)
  schema_location: /kdf/schemas/orders  # Where to store inferred schema
  schema_evolution_mode: addNewColumns  # How to handle schema changes
  infer_column_types: true  # Automatically detect data types
  include_existing_files: true  # Process existing files on first run
  rescue_data_column: _rescued_data  # Column for malformed records

  # Performance tuning
  max_files_per_trigger: 1000  # Limit files processed per batch
  max_bytes_per_trigger: "10g"  # Limit data processed per batch

  # Advanced: Use cloud notifications for near-instant processing
  use_notifications: false  # Requires cloud provider setup
```

---

## Schema Evolution

Autoloader handles schema changes automatically based on the `schema_evolution_mode`:

### `addNewColumns` (Default - Recommended)

New columns are added automatically. Best for most cases.

```yaml
schema_evolution_mode: addNewColumns
```

**Example**:
```
Day 1: {id, name, email}
Day 2: {id, name, email, phone}  # ✅ "phone" column added
```

### `rescue`

New columns go to rescue column. Best for strict schemas.

```yaml
schema_evolution_mode: rescue
rescue_data_column: _rescued_data
```

**Example**:
```
Day 1: {id, name, email}
Day 2: {id, name, email, _rescued_data}  # New fields in _rescued_data
```

### `failOnNewColumns`

Fail if new columns appear. Best for production with controlled schemas.

```yaml
schema_evolution_mode: failOnNewColumns
```

---

## Usage Patterns

### Pattern 1: Bronze Layer Ingestion

Most common - ingest raw data incrementally.

```yaml
name: bronze_orders
execution_mode: streaming  # Or micro_batch
checkpoint_location: /kdf/checkpoints/bronze_orders

source:
  type: s3
  path: s3://my-bucket/raw/orders/
  format: json
  use_autoloader: true  # Default
  schema_location: /kdf/schemas/orders
  schema_evolution_mode: addNewColumns

target:
  type: delta
  path: /medallion/bronze/orders
  mode: append
```

**Result**:
- First run: Processes all existing files
- Subsequent runs: Only new files
- Schema adapts automatically
- Efficient and cost-effective

---

### Pattern 2: Batch with Autoloader Benefits

Even for batch jobs, Autoloader provides benefits.

```yaml
name: daily_orders_load
execution_mode: batch  # Batch mode

source:
  type: s3
  path: s3://my-bucket/orders/date=2024-01-*/
  format: parquet
  use_autoloader: true
  schema_location: /kdf/schemas/orders_daily
  infer_column_types: true

target:
  type: delta
  path: /data/orders
  mode: overwrite
```

**Benefits**:
- Automatic schema inference (no manual schema definition)
- Schema evolution handling
- Rescue column for data quality

---

### Pattern 3: Near-Instant Processing with Notifications

For latency-sensitive use cases (requires cloud setup).

```yaml
source:
  type: s3
  path: s3://my-bucket/realtime/events/
  format: json
  use_autoloader: true
  use_notifications: true  # Enables S3 Event Notifications → SQS
  schema_location: /kdf/schemas/events
  max_files_per_trigger: 100  # Small batches for low latency
```

**Setup Required**:
1. Configure S3 Event Notifications
2. Create SQS queue
3. Configure Databricks to read from SQS

**Result**: Files processed within seconds of landing.

---

### Pattern 4: Handling Malformed Data

Capture bad records instead of failing.

```yaml
source:
  type: s3
  path: s3://my-bucket/messy-data/
  format: csv
  use_autoloader: true
  schema_evolution_mode: rescue
  rescue_data_column: _rescued_data
```

**Malformed records** go to `_rescued_data` column:
```python
# Query bad records
bad_records = df.filter(col("_rescued_data").isNotNull())
```

---

## Performance Tuning

### Control Processing Rate

```yaml
# Limit files per trigger
max_files_per_trigger: 1000

# Limit data per trigger
max_bytes_per_trigger: "10g"
```

**Use cases**:
- Prevent overwhelming downstream systems
- Control cluster costs
- Ensure consistent processing times

### Optimize for Small Files

```yaml
# More files per trigger for small files
max_files_per_trigger: 10000
max_bytes_per_trigger: "5g"
```

### Optimize for Large Files

```yaml
# Fewer files per trigger for large files
max_files_per_trigger: 100
max_bytes_per_trigger: "50g"
```

---

## Schema Management

### Automatic Schema Storage

Autoloader stores inferred schemas in the `schema_location`:

```yaml
schema_location: /kdf/schemas/orders
```

This location contains:
- Inferred schema metadata
- Schema evolution history
- Column type inference results

### View Schema History

```python
# Read schema location as Delta table
schema_df = spark.read.format("delta").load("/kdf/schemas/orders/_schemas")
schema_df.orderBy("version").show()
```

### Manual Schema Override

If needed, provide explicit schema:

```python
from pyspark.sql.types import StructType, StructField, StringType, IntegerType

manual_schema = StructType([
    StructField("id", IntegerType(), nullable=False),
    StructField("name", StringType(), nullable=True),
    StructField("email", StringType(), nullable=True),
])

# In KDF connector code, you can pass schema
df = reader.schema(manual_schema).load(path)
```

---

## Monitoring

### File Processing Metrics

Autoloader provides rich metrics:

```python
# In streaming query
query = df.writeStream \
    .format("delta") \
    .option("checkpointLocation", checkpoint_path) \
    .start(target_path)

# View progress
query.lastProgress
```

**Metrics include**:
- `numInputRows` - Records processed
- `inputRowsPerSecond` - Throughput
- `sources[].numInputFiles` - Files processed
- `sources[].latestFileAge` - File discovery latency

### Query KDF Metadata

```sql
SELECT
  pipeline_name,
  records_read,
  records_written,
  execution_time_seconds,
  metadata->>'files_processed' as files_processed
FROM delta.`/kdf/metadata/pipeline_runs`
WHERE source_type = 's3'
  AND use_autoloader = true
ORDER BY start_time DESC;
```

---

## Comparison

| Feature | Standard Read | Autoloader |
|---------|--------------|------------|
| **Incremental** | ❌ Reads all files | ✅ Only new files |
| **Schema Inference** | Manual | ✅ Automatic |
| **Schema Evolution** | ❌ Breaks | ✅ Handles automatically |
| **File Listing** | Slow (recursive) | ✅ Fast (cloud APIs) |
| **Malformed Data** | ❌ Fails | ✅ Rescue column |
| **Checkpointing** | Manual | ✅ Built-in |
| **Notifications** | ❌ Not supported | ✅ Near-instant |
| **Cost** | High (re-reads) | ✅ Low (incremental) |
| **Performance** | Degrades over time | ✅ Consistent |

---

## When to Disable Autoloader

Autoloader is recommended for **most** scenarios, but you can disable it:

```yaml
source:
  type: s3
  path: s3://bucket/data/
  format: csv
  use_autoloader: false  # Use standard Spark read
```

**Disable when**:
- Reading a **static** dataset (won't change)
- Need to re-process all files every time
- Using file formats not supported by Autoloader
- Testing/debugging specific file read behavior

---

## Best Practices

### 1. Always Set Schema Location

```yaml
schema_location: /kdf/schemas/${pipeline_name}
```

Allows schema evolution and recovery.

### 2. Use Rescue Column in Production

```yaml
rescue_data_column: _rescued_data
```

Captures malformed records instead of failing.

### 3. Monitor Schema Changes

```sql
-- Alert on schema changes
SELECT * FROM delta.`/kdf/schemas/orders/_schemas`
WHERE version > (SELECT MAX(version) - 1 FROM delta.`/kdf/schemas/orders/_schemas`)
```

### 4. Tune for Your Workload

```yaml
# High-throughput: More files
max_files_per_trigger: 10000

# Low-latency: Fewer files
max_files_per_trigger: 100
```

### 5. Use Notifications for Real-time

For sub-minute latency, set up cloud notifications:

```yaml
use_notifications: true
```

### 6. Partition Bronze Layer

```yaml
target:
  path: /bronze/orders
  partition_by: [year, month, day]
```

Improves query performance.

---

## Migration from Standard Read

### Before

```yaml
source:
  type: s3
  path: s3://bucket/orders/
  format: csv
  # Standard Spark read
```

### After

```yaml
source:
  type: s3
  path: s3://bucket/orders/
  format: csv
  use_autoloader: true  # Now default!
  schema_location: /kdf/schemas/orders
  schema_evolution_mode: addNewColumns
```

**Changes**:
- ✅ Incremental processing (only new files)
- ✅ Automatic schema evolution
- ✅ Better performance
- ✅ Lower costs

---

## Troubleshooting

### Schema Conflict Error

```
AnalysisException: A schema mismatch detected when restoring...
```

**Solution**: Reset schema location or use `rescue` mode:
```yaml
schema_evolution_mode: rescue
```

### Files Not Being Processed

Check:
1. `include_existing_files: true` for first run
2. Checkpoint location is correct
3. S3 permissions are set
4. File glob filter if specified

### Performance Issues

Tune processing limits:
```yaml
max_files_per_trigger: 1000
max_bytes_per_trigger: "10g"
```

---

## Summary

KDF S3 connector now uses **Autoloader by default** for:

✅ **Incremental Processing** - Only new files
✅ **Automatic Schema** - Inference and evolution
✅ **Efficient Discovery** - Fast cloud APIs
✅ **Data Quality** - Rescue column for bad records
✅ **Performance** - Consistent, predictable
✅ **Cost-Effective** - No redundant reads
✅ **Production-Ready** - Battle-tested at scale

**Simply use S3 connector - Autoloader works automatically!**

```yaml
source:
  type: s3
  path: s3://my-bucket/data/
  format: csv
  # Autoloader enabled by default ✅
```

---

**Next**: See [MODERN_CICD.md](./MODERN_CICD.md) for deployment with Asset Bundles
