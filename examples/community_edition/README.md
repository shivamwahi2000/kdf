# Testing KDF on Databricks Community Edition

## Overview

This guide helps you test KDF on **Databricks Community Edition** (free tier).

**What you can test:**
✅ S3 Autoloader for incremental file processing
✅ Medallion pipeline execution (Bronze → Silver → Gold)
✅ Delta Lake operations
✅ Data quality checks
✅ All data skills (deduplicate, aggregate, etc.)

**Limitations:**
❌ No Databricks Asset Bundles (requires paid tier)
❌ No scheduled jobs/workflows
❌ Single-node cluster only
❌ 15GB RAM, 2 cores

For full feature testing (Asset Bundles, CI/CD), use the [14-day free trial](https://databricks.com/try-databricks).

---

## Quick Start

### Step 1: Sign Up for Community Edition

1. Go to https://community.cloud.databricks.com/
2. Sign up with email (free, no credit card)
3. Verify email and log in

### Step 2: Create a Cluster

1. In sidebar: **Compute** → **Create Cluster**
2. Settings:
   - **Name**: kdf-test
   - **Runtime**: 13.3 LTS or newer
   - **Mode**: Single Node (only option on Community Edition)
3. Click **Create Cluster** (takes 3-5 minutes)

### Step 3: Upload KDF Notebook

1. Download the test notebook (see below)
2. In sidebar: **Workspace** → **Users** → your email
3. Click **⋮** → **Import**
4. Upload `kdf_community_test.py`

### Step 4: Run Test

1. Open the notebook
2. Attach to your cluster
3. Run all cells
4. See KDF in action!

---

## Test Scenarios

### Scenario 1: S3 Autoloader Test (Recommended)

Test incremental file processing with Autoloader.

**Setup:**
```python
# In Databricks notebook
# Create sample data locally (simulating S3)
import pandas as pd
from datetime import datetime, timedelta

# Day 1 data
df1 = pd.DataFrame({
    'id': range(1, 101),
    'name': [f'Customer_{i}' for i in range(1, 101)],
    'amount': [100 + i for i in range(1, 101)],
    'date': [datetime.now().date()] * 100
})

# Save as CSV
df1.to_csv('/dbfs/tmp/kdf_test/raw/day1/orders.csv', index=False)

# Day 2 data (new files)
df2 = pd.DataFrame({
    'id': range(101, 201),
    'name': [f'Customer_{i}' for i in range(101, 201)],
    'amount': [100 + i for i in range(101, 201)],
    'date': [(datetime.now() + timedelta(days=1)).date()] * 100
})

df2.to_csv('/dbfs/tmp/kdf_test/raw/day2/orders.csv', index=False)
```

**Run KDF with Autoloader:**
```python
# Install KDF (if not pre-installed)
# %pip install git+https://github.com/shivamwahi2000/kdf.git

from pyspark.sql import SparkSession
from kdf.core.config import PipelineConfig
from kdf.core.pipeline import Pipeline
from kdf.bootstrap import bootstrap_registries

# Bootstrap KDF
bootstrap_registries()

# Create config
config = PipelineConfig(
    name="autoloader_test",
    execution_mode="streaming",

    source={
        "type": "s3",
        "path": "file:///dbfs/tmp/kdf_test/raw/",  # Use local file:// on Community Edition
        "format": "csv",
        "use_autoloader": True,
        "schema_location": "/tmp/kdf_schemas/orders",
        "schema_evolution_mode": "addNewColumns",
        "include_existing_files": True
    },

    target={
        "type": "delta",
        "path": "/tmp/kdf_bronze/orders",
        "mode": "append"
    },

    checkpoint_location="/tmp/kdf_checkpoints/autoloader_test"
)

# Run pipeline
pipeline = Pipeline(config)

# For streaming, we need to run for a short time
query = pipeline.run_streaming(max_iterations=2)  # Process 2 micro-batches

# Check results
bronze_df = spark.read.format("delta").load("/tmp/kdf_bronze/orders")
print(f"Total records: {bronze_df.count()}")
bronze_df.show(5)
```

**Expected Output:**
- First run: Processes both day1 and day2 (200 records)
- Add more files to `/dbfs/tmp/kdf_test/raw/day3/`
- Second run: Only processes day3 (incremental!)

---

### Scenario 2: Simple Medallion Pipeline

Test Bronze → Silver → Gold on local data.

**Bronze Layer:**
```python
from kdf.core.config import PipelineConfig
from kdf.core.pipeline import Pipeline

# Bronze: Ingest raw data
bronze_config = PipelineConfig(
    name="bronze_orders",

    source={
        "type": "s3",
        "path": "file:///dbfs/tmp/kdf_test/raw/",
        "format": "csv",
        "use_autoloader": False  # Use batch for simplicity
    },

    target={
        "type": "delta",
        "path": "/tmp/medallion/bronze/orders",
        "mode": "overwrite"
    }
)

bronze_pipeline = Pipeline(bronze_config)
bronze_result = bronze_pipeline.run()

print(f"✓ Bronze: {bronze_result.metrics['records_written']} records")
```

**Silver Layer:**
```python
# Silver: Clean and validate
silver_config = PipelineConfig(
    name="silver_orders",

    source={
        "type": "delta",
        "path": "/tmp/medallion/bronze/orders"
    },

    skills=[
        {
            "deduplicate": {
                "keys": ["id"],
                "order_by": "date"
            }
        }
    ],

    quality=[
        {
            "not_null": {
                "columns": ["id", "name", "amount"]
            }
        }
    ],

    target={
        "type": "delta",
        "path": "/tmp/medallion/silver/orders",
        "mode": "overwrite"
    }
)

silver_pipeline = Pipeline(silver_config)
silver_result = silver_pipeline.run()

print(f"✓ Silver: {silver_result.metrics['records_written']} records")
```

**Gold Layer:**
```python
# Gold: Business metrics
gold_config = PipelineConfig(
    name="gold_revenue",

    source={
        "type": "delta",
        "path": "/tmp/medallion/silver/orders"
    },

    skills=[
        {
            "aggregate": {
                "group_by": ["date"],
                "metrics": [
                    {"name": "total_revenue", "agg": "sum", "column": "amount"},
                    {"name": "order_count", "agg": "count"},
                    {"name": "avg_order_value", "agg": "avg", "column": "amount"}
                ]
            }
        }
    ],

    target={
        "type": "delta",
        "path": "/tmp/medallion/gold/revenue",
        "mode": "overwrite"
    }
)

gold_pipeline = Pipeline(gold_config)
gold_result = gold_pipeline.run()

# View results
gold_df = spark.read.format("delta").load("/tmp/medallion/gold/revenue")
gold_df.show()
```

---

### Scenario 3: Data Quality Testing

Test quality checks and rescue data.

```python
# Create data with some bad records
import pandas as pd

good_data = pd.DataFrame({
    'id': [1, 2, 3],
    'name': ['Alice', 'Bob', 'Charlie'],
    'email': ['alice@example.com', 'bob@example.com', 'charlie@example.com']
})

bad_data = pd.DataFrame({
    'id': [4, None, 6],  # Missing ID
    'name': ['Dave', 'Eve', None],  # Missing name
    'email': ['dave@example.com', 'eve@example.com', 'frank@example.com']
})

combined = pd.concat([good_data, bad_data])
combined.to_csv('/dbfs/tmp/kdf_test/quality/data.csv', index=False)

# Run pipeline with quality checks
quality_config = PipelineConfig(
    name="quality_test",

    source={
        "type": "s3",
        "path": "file:///dbfs/tmp/kdf_test/quality/",
        "format": "csv"
    },

    quality=[
        {
            "not_null": {
                "columns": ["id", "name", "email"]
            }
        }
    ],

    target={
        "type": "delta",
        "path": "/tmp/kdf_quality_test",
        "mode": "overwrite"
    }
)

try:
    quality_pipeline = Pipeline(quality_config)
    result = quality_pipeline.run()
except Exception as e:
    print(f"Quality check failed as expected: {e}")
    # Check quality metadata
    # (Quality violations are logged to metadata)
```

---

## Sample Notebook

Save this as `kdf_community_test.py`:

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # KDF Community Edition Test
# MAGIC
# MAGIC This notebook tests KDF on Databricks Community Edition (free tier).

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

# Install KDF
%pip install git+https://github.com/shivamwahi2000/kdf.git

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from pyspark.sql import SparkSession
from kdf.bootstrap import bootstrap_registries
from kdf.core.config import PipelineConfig
from kdf.core.pipeline import Pipeline
import pandas as pd
from datetime import datetime

# Bootstrap KDF
bootstrap_registries()

print("✓ KDF loaded successfully!")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Create Sample Data

# COMMAND ----------

# Clean up previous runs
dbutils.fs.rm("/tmp/kdf_test", True)
dbutils.fs.rm("/tmp/medallion", True)

# Create sample orders data
orders_data = pd.DataFrame({
    'order_id': range(1, 101),
    'customer_id': [f'CUST_{i%20}' for i in range(1, 101)],
    'product': [f'Product_{i%10}' for i in range(1, 101)],
    'amount': [50 + (i * 1.5) for i in range(1, 101)],
    'order_date': [datetime.now().date()] * 100,
    'updated_at': [datetime.now()] * 100
})

# Save to DBFS
orders_data.to_csv('/dbfs/tmp/kdf_test/raw/orders.csv', index=False)

print(f"✓ Created {len(orders_data)} sample orders")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 1: Bronze Layer (Raw Ingestion)

# COMMAND ----------

bronze_config = PipelineConfig(
    name="bronze_orders",

    source={
        "type": "s3",
        "path": "file:///dbfs/tmp/kdf_test/raw/",
        "format": "csv",
        "use_autoloader": False  # Batch mode for simplicity
    },

    target={
        "type": "delta",
        "path": "/tmp/medallion/bronze/orders",
        "mode": "overwrite"
    }
)

bronze_pipeline = Pipeline(bronze_config)
bronze_result = bronze_pipeline.run()

print(f"\n✓ Bronze Layer Complete")
print(f"  Records written: {bronze_result.metrics.get('records_written', 'N/A')}")

# View data
bronze_df = spark.read.format("delta").load("/tmp/medallion/bronze/orders")
bronze_df.show(5)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 2: Silver Layer (Clean & Validate)

# COMMAND ----------

silver_config = PipelineConfig(
    name="silver_orders",

    source={
        "type": "delta",
        "path": "/tmp/medallion/bronze/orders"
    },

    skills=[
        {
            "deduplicate": {
                "keys": ["order_id"],
                "order_by": "updated_at"
            }
        }
    ],

    quality=[
        {
            "not_null": {
                "columns": ["order_id", "customer_id", "amount"]
            }
        },
        {
            "unique": {
                "columns": ["order_id"]
            }
        }
    ],

    target={
        "type": "delta",
        "path": "/tmp/medallion/silver/orders",
        "mode": "overwrite"
    }
)

silver_pipeline = Pipeline(silver_config)
silver_result = silver_pipeline.run()

print(f"\n✓ Silver Layer Complete")
print(f"  Records written: {silver_result.metrics.get('records_written', 'N/A')}")

# View data
silver_df = spark.read.format("delta").load("/tmp/medallion/silver/orders")
silver_df.show(5)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 3: Gold Layer (Business Metrics)

# COMMAND ----------

gold_config = PipelineConfig(
    name="gold_customer_metrics",

    source={
        "type": "delta",
        "path": "/tmp/medallion/silver/orders"
    },

    skills=[
        {
            "aggregate": {
                "group_by": ["customer_id"],
                "metrics": [
                    {"name": "total_spent", "agg": "sum", "column": "amount"},
                    {"name": "order_count", "agg": "count"},
                    {"name": "avg_order_value", "agg": "avg", "column": "amount"},
                    {"name": "max_order", "agg": "max", "column": "amount"}
                ]
            }
        }
    ],

    target={
        "type": "delta",
        "path": "/tmp/medallion/gold/customer_metrics",
        "mode": "overwrite"
    }
)

gold_pipeline = Pipeline(gold_config)
gold_result = gold_pipeline.run()

print(f"\n✓ Gold Layer Complete")
print(f"  Records written: {gold_result.metrics.get('records_written', 'N/A')}")

# View results
gold_df = spark.read.format("delta").load("/tmp/medallion/gold/customer_metrics")
gold_df.orderBy("total_spent", ascending=False).show(10)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Test 4: S3 Autoloader (Incremental)

# COMMAND ----------

# Create additional data (simulating new files)
new_orders = pd.DataFrame({
    'order_id': range(101, 151),
    'customer_id': [f'CUST_{i%20}' for i in range(101, 151)],
    'product': [f'Product_{i%10}' for i in range(101, 151)],
    'amount': [50 + (i * 1.5) for i in range(101, 151)],
    'order_date': [datetime.now().date()] * 50,
    'updated_at': [datetime.now()] * 50
})

# Save to new directory (simulating new day)
new_orders.to_csv('/dbfs/tmp/kdf_test/raw_incremental/day2/orders.csv', index=False)

print("✓ Created incremental data")

# COMMAND ----------

# Run with Autoloader
autoloader_config = PipelineConfig(
    name="autoloader_test",
    execution_mode="batch",  # For testing, use batch mode

    source={
        "type": "s3",
        "path": "file:///dbfs/tmp/kdf_test/raw_incremental/",
        "format": "csv",
        "use_autoloader": True,  # This is the key!
        "schema_location": "/tmp/kdf_schemas/autoloader_test",
        "schema_evolution_mode": "addNewColumns",
        "include_existing_files": True
    },

    target={
        "type": "delta",
        "path": "/tmp/kdf_autoloader_test",
        "mode": "append"
    }
)

autoloader_pipeline = Pipeline(autoloader_config)
autoloader_result = autoloader_pipeline.run()

print(f"\n✓ Autoloader Test Complete")
print(f"  Records written: {autoloader_result.metrics.get('records_written', 'N/A')}")

# View results
autoloader_df = spark.read.format("delta").load("/tmp/kdf_autoloader_test")
print(f"  Total records in table: {autoloader_df.count()}")
autoloader_df.show(5)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("="*60)
print("KDF Community Edition Test Summary")
print("="*60)
print(f"✓ Bronze Layer: {bronze_result.metrics.get('records_written', 0)} records")
print(f"✓ Silver Layer: {silver_result.metrics.get('records_written', 0)} records")
print(f"✓ Gold Layer: {gold_result.metrics.get('records_written', 0)} records")
print(f"✓ Autoloader: {autoloader_result.metrics.get('records_written', 0)} records")
print("="*60)
print("\nAll tests passed! KDF is working on Community Edition.")
print("\nNext steps:")
print("  1. Try with your own data")
print("  2. Explore more skills (reconcile, schema_evolution)")
print("  3. For full features (Asset Bundles, CI/CD), get 14-day trial")
print("="*60)

# COMMAND ----------
```

---

## Limitations & Workarounds

### Limitation 1: No Real S3 Access

**Workaround**: Use `file://` protocol with DBFS
```yaml
source:
  path: "file:///dbfs/tmp/my_data/"  # Instead of s3://bucket/
```

### Limitation 2: No Databricks Asset Bundles

**Workaround**: Run pipelines manually in notebooks
```python
# Instead of: databricks bundle deploy
# Use: Run notebook cells
```

### Limitation 3: No Scheduled Jobs

**Workaround**: Run manually or use external scheduler
```python
# Manual execution in notebook
pipeline = Pipeline(config)
result = pipeline.run()
```

### Limitation 4: Limited Resources

**Workaround**: Use small datasets (<1GB)
```python
# Test with sample data
df.limit(1000)  # Work with samples
```

---

## Upgrading to Paid Tier

When ready for production testing:

1. **Free Trial** (14 days): https://databricks.com/try-databricks
   - All features including Asset Bundles
   - Multi-node clusters
   - Scheduled jobs
   - Full CI/CD testing

2. **After Trial**: Pay-as-you-go pricing
   - AWS: $0.40-0.75/DBU
   - Azure: Similar pricing
   - Can still use small clusters for testing

---

## FAQ

**Q: Can I test S3 Autoloader on Community Edition?**
A: Yes! Use `file://` protocol with local data. The Autoloader functionality works the same.

**Q: Can I test Asset Bundles?**
A: No. Asset Bundles require the Jobs API which isn't available on Community Edition. Use the 14-day trial.

**Q: How long can I use Community Edition?**
A: Forever! No time limit, but clusters auto-terminate after 2 hours of inactivity.

**Q: Can I connect to real S3?**
A: No direct AWS integration on Community Edition. Use DBFS or upload files manually.

**Q: Is the test representative of production?**
A: Core KDF features yes, CI/CD features no. For full production testing, use the trial.

---

## Summary

✅ **Can Test on Community Edition:**
- S3 Autoloader (with local files)
- Medallion pipelines
- All data skills
- Quality checks
- Delta Lake operations

❌ **Need Paid Tier For:**
- Asset Bundles
- Scheduled workflows
- Real S3 integration
- Multi-node clusters
- Production CI/CD

**Recommendation**:
1. Start with Community Edition to learn KDF
2. Get 14-day trial to test Asset Bundles and CI/CD
3. Use pay-as-you-go for production

---

**Ready to test? Upload the notebook and run! 🚀**
