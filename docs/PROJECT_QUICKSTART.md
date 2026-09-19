# Creating New Projects with KDF

This guide shows how to use KDF as a framework to bootstrap new data engineering projects.

---

## What You Get

When you create a new project with KDF, you get a **production-ready data engineering template** with:

✅ **Medallion Architecture** - Bronze → Silver → Gold layers
✅ **Example Pipelines** - Ready-to-customize configurations
✅ **Databricks Integration** - Asset Bundles for deployment
✅ **CI/CD Workflows** - GitHub Actions pre-configured
✅ **Best Practices** - Project structure and patterns
✅ **Documentation** - Project-specific README

---

## Quick Start

### 1. Install KDF

```bash
# From PyPI (recommended)
pip install kdf

# Or from GitHub
pip install git+https://github.com/shivamwahi2000/kdf.git
```

### 2. Create Your Project

```bash
kdf init project my-data-project
```

This creates:

```
my-data-project/
├── configs/
│   ├── pipelines/              # Pipeline configurations
│   │   ├── bronze_orders.yaml       # Raw ingestion
│   │   ├── silver_orders.yaml       # Clean & validate
│   │   ├── gold_daily_revenue.yaml  # Business metrics
│   │   └── medallion_orders.yaml    # Complete workflow
│   ├── databricks/
│   │   └── job.yml             # Databricks job definition
│   └── environments.yaml       # Environment settings
├── notebooks/                  # Databricks notebooks (empty)
├── scripts/                    # Utility scripts (empty)
├── tests/                      # Tests (empty)
├── docs/                       # Documentation (empty)
├── .github/workflows/
│   └── deploy-dev.yml          # CI/CD workflow
├── databricks.yml              # Databricks Asset Bundle config
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
└── README.md                   # Project documentation
```

### 3. Install Dependencies

```bash
cd my-data-project
pip install -r requirements.txt
```

### 4. Configure Your Environment

Edit `.env` (create from template):

```bash
# Database
POSTGRES_HOST=your-db-host.com
POSTGRES_PORT=5432
POSTGRES_DATABASE=production
POSTGRES_USER=your-user
POSTGRES_PASSWORD=your-password

# AWS
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Environment
ENVIRONMENT=dev
```

### 5. Run Your First Pipeline

```bash
# Validate configuration
kdf validate configs/pipelines/bronze_orders.yaml

# Run pipeline
kdf run configs/pipelines/bronze_orders.yaml
```

---

## Customization Options

### Minimal Project (No Databricks/CI-CD)

```bash
kdf init project my-project \
  --no-databricks \
  --no-cicd \
  --no-example-pipelines
```

Creates minimal structure with just config directories.

### Custom Location

```bash
kdf init project my-project --path /projects
```

Creates project in `/projects/my-project`.

### Full Options

```bash
kdf init project my-project \
  --path /projects \
  --databricks \               # Include Databricks integration (default: true)
  --cicd \                     # Include CI/CD workflows (default: true)
  --example-pipelines          # Include example pipelines (default: true)
```

---

## Example Pipelines Explained

### Bronze Layer (`bronze_orders.yaml`)

**Purpose**: Ingest raw data from PostgreSQL

```yaml
name: bronze_orders
description: Ingest raw orders from PostgreSQL to Bronze layer
execution_mode: batch

source:
  type: postgres
  host: ${env.POSTGRES_HOST}
  port: 5432
  database: production
  schema: public
  table: orders
  incremental:
    column: updated_at
    start: "2024-01-01"

target:
  type: delta
  path: ${env.data_path}/bronze/orders
  mode: append
  partition_by: [order_date]

metadata:
  enabled: true
  path: ${env.metadata_path}
```

**Key Features**:
- Incremental loading (only new/updated records)
- Partitioned by `order_date` for query performance
- Metadata tracking enabled

**Run**:
```bash
kdf run configs/pipelines/bronze_orders.yaml
```

---

### Silver Layer (`silver_orders.yaml`)

**Purpose**: Clean and validate data

```yaml
name: silver_orders
description: Clean and validate orders in Silver layer
execution_mode: batch

source:
  type: delta
  path: ${env.data_path}/bronze/orders

skills:
  - deduplicate:
      keys: [order_id]
      order_by: updated_at

quality:
  - not_null:
      columns: [order_id, customer_id, order_date]
  - unique:
      columns: [order_id]

target:
  type: delta
  path: ${env.data_path}/silver/orders
  mode: overwrite
  partition_by: [order_date]

metadata:
  enabled: true
  path: ${env.metadata_path}
```

**Key Features**:
- Deduplication by `order_id`
- Data quality checks (not_null, unique)
- Overwrites on each run (idempotent)

**Run**:
```bash
kdf run configs/pipelines/silver_orders.yaml
```

---

### Gold Layer (`gold_daily_revenue.yaml`)

**Purpose**: Calculate business metrics

```yaml
name: gold_daily_revenue
description: Calculate daily revenue metrics
execution_mode: batch

source:
  type: delta
  path: ${env.data_path}/silver/orders

skills:
  - aggregate:
      group_by: [order_date, product_category]
      metrics:
        - name: total_revenue
          agg: sum
          column: amount
        - name: order_count
          agg: count
        - name: avg_order_value
          agg: avg
          column: amount
        - name: unique_customers
          agg: countDistinct
          column: customer_id

target:
  type: delta
  path: ${env.data_path}/gold/daily_revenue
  mode: overwrite

metadata:
  enabled: true
  path: ${env.metadata_path}
```

**Key Features**:
- Aggregations by date and category
- Multiple metrics calculated
- Analytics-ready data

**Run**:
```bash
kdf run configs/pipelines/gold_daily_revenue.yaml
```

---

### Medallion Workflow (`medallion_orders.yaml`)

**Purpose**: Run all layers with dependency management

```yaml
name: medallion_orders
description: Complete Medallion architecture for orders

pipelines:
  - name: bronze_orders
    config_file: configs/pipelines/bronze_orders.yaml

  - name: silver_orders
    config_file: configs/pipelines/silver_orders.yaml
    depends_on: [bronze_orders]

  - name: gold_daily_revenue
    config_file: configs/pipelines/gold_daily_revenue.yaml
    depends_on: [silver_orders]

metadata:
  enabled: true
  path: ${env.metadata_path}
```

**Run**:
```bash
kdf run-medallion configs/pipelines/medallion_orders.yaml
```

**Output**:
```
🚀 Running medallion pipeline: medallion_orders
📊 Pipelines: 3
🔗 Dependencies: 2

Running pipeline: bronze_orders
✓ bronze_orders completed (23.4s)
  Records read: 10,523
  Records written: 10,523

Running pipeline: silver_orders
✓ silver_orders completed (15.2s)
  Records read: 10,523
  Records written: 10,489

Running pipeline: gold_daily_revenue
✓ gold_daily_revenue completed (8.1s)
  Records read: 10,489
  Records written: 365

✓ Medallion pipeline completed!
  Total time: 46.7s
```

---

## Customizing for Your Use Case

### Step 1: Update Data Sources

Edit `configs/pipelines/bronze_*.yaml` files:

```yaml
source:
  type: postgres  # or s3, delta, kafka
  host: your-database.com
  table: your_table
```

### Step 2: Add Your Skills

Edit `configs/pipelines/silver_*.yaml`:

```yaml
skills:
  - deduplicate:
      keys: [your_id_column]
  - your_custom_skill:
      param: value
```

### Step 3: Define Your Metrics

Edit `configs/pipelines/gold_*.yaml`:

```yaml
skills:
  - aggregate:
      group_by: [your_dimensions]
      metrics:
        - name: your_metric
          agg: sum
          column: your_column
```

### Step 4: Update Environments

Edit `configs/environments.yaml`:

```yaml
environments:
  dev:
    data_path: /tmp/data/dev
    checkpoint_path: /tmp/checkpoints/dev
    metadata_path: /tmp/metadata/dev

  production:
    data_path: s3://your-bucket/data/production
    checkpoint_path: s3://your-bucket/checkpoints/production
    metadata_path: s3://your-bucket/metadata/production
```

---

## Deploying to Databricks

### Step 1: Install Databricks CLI

```bash
# macOS/Linux
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

# Or download from https://github.com/databricks/cli/releases
```

### Step 2: Authenticate

```bash
databricks auth login --host https://your-workspace.cloud.databricks.com
```

### Step 3: Update Bundle Configuration

Edit `databricks.yml`:

```yaml
bundle:
  name: my_data_project

targets:
  dev:
    workspace:
      host: ${var.databricks_host_dev}

  production:
    workspace:
      host: ${var.databricks_host_prod}
```

### Step 4: Deploy

```bash
# Validate bundle
databricks bundle validate -t dev

# Deploy to dev
databricks bundle deploy -t dev

# Run job
databricks bundle run -t dev my_data_project_pipeline
```

---

## Setting Up CI/CD

### GitHub Actions (Included)

The project includes `.github/workflows/deploy-dev.yml`:

```yaml
name: Deploy to Dev

on:
  push:
    branches: [develop]

jobs:
  deploy-dev:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install KDF
        run: pip install kdf
      - name: Validate configurations
        run: kdf validate configs/pipelines/*.yaml
      - name: Deploy to Databricks
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST_DEV }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN_DEV }}
        run: databricks bundle deploy -t dev
```

### Setup Steps

1. **Add GitHub Secrets**:
   - `DATABRICKS_HOST_DEV`
   - `DATABRICKS_TOKEN_DEV`
   - `DATABRICKS_HOST_PROD`
   - `DATABRICKS_TOKEN_PROD`

2. **Push to Trigger**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/your-org/my-data-project.git
   git push origin develop  # Triggers dev deployment
   ```

---

## Monitoring Your Pipelines

### View Pipeline Status

```bash
kdf status
```

**Output**:
```
Pipeline             Status     Start Time            Read      Written
bronze_orders        SUCCESS    2024-01-15 10:23:14   10,523    10,523
silver_orders        SUCCESS    2024-01-15 10:23:37   10,523    10,489
gold_daily_revenue   SUCCESS    2024-01-15 10:23:52   10,489    365
```

### Query Metadata

```sql
-- Recent pipeline runs
SELECT
  pipeline_name,
  status,
  records_read,
  records_written,
  execution_time_seconds,
  start_time,
  end_time
FROM delta.`${env.metadata_path}/pipeline_runs`
WHERE DATE(start_time) = CURRENT_DATE()
ORDER BY start_time DESC;

-- Data quality issues
SELECT
  pipeline_name,
  check_name,
  failed,
  check_time
FROM delta.`${env.metadata_path}/quality_checks`
WHERE failed > 0
ORDER BY check_time DESC;

-- Pipeline lineage
SELECT
  pipeline_name,
  source_type,
  source_path,
  target_path
FROM delta.`${env.metadata_path}/pipelines`
WHERE pipeline_name LIKE '%orders%';
```

---

## Real-World Examples

### E-commerce Analytics

```bash
kdf init project ecommerce-analytics
cd ecommerce-analytics

# Configure sources in configs/pipelines/
# - bronze_orders.yaml → PostgreSQL orders table
# - bronze_customers.yaml → PostgreSQL customers table
# - bronze_clickstream.yaml → S3 clickstream events (with Autoloader)

# Run medallion workflow
kdf run-medallion configs/pipelines/medallion_ecommerce.yaml
```

### IoT Sensor Data

```bash
kdf init project iot-sensors
cd iot-sensors

# Configure sources
# - bronze_sensors.yaml → S3 sensor readings (JSON, Autoloader)
# - bronze_alerts.yaml → Kafka real-time alerts

# Run streaming pipeline
kdf run configs/pipelines/bronze_sensors.yaml
```

### Financial Reporting

```bash
kdf init project financial-reports
cd financial-reports

# Configure sources
# - bronze_transactions.yaml → PostgreSQL transactions
# - silver_transactions.yaml → Clean + quality checks
# - gold_daily_summary.yaml → Daily financial metrics

# Run with strict quality checks
kdf run configs/pipelines/silver_transactions.yaml
```

---

## Best Practices

### 1. Start Simple

```bash
# Create minimal project
kdf init project my-project --no-example-pipelines

# Add one pipeline at a time
# Test each pipeline before adding the next
```

### 2. Use Environment Variables

```yaml
# ✅ Good - Uses environment variables
source:
  host: ${env.POSTGRES_HOST}
  password: ${env.POSTGRES_PASSWORD}

# ❌ Bad - Hardcoded credentials
source:
  host: prod-db.example.com
  password: mysecretpassword
```

### 3. Enable Metadata Tracking

```yaml
# Always include metadata
metadata:
  enabled: true
  path: ${env.metadata_path}
```

### 4. Add Quality Checks

```yaml
# Every Silver pipeline should have quality checks
quality:
  - not_null:
      columns: [id, created_at]
  - unique:
      columns: [id]
```

### 5. Partition Large Tables

```yaml
# Partition by date for better query performance
target:
  partition_by: [year, month, day]
```

---

## Troubleshooting

### "Directory already exists"

```bash
# Project name must be unique
kdf init project my-project  # ❌ Fails if exists
kdf init project my-project-v2  # ✅ Works
```

### Configuration Validation Errors

```bash
# Validate before running
kdf validate configs/pipelines/bronze_orders.yaml
```

### Databricks Deployment Issues

```bash
# Check bundle configuration
databricks bundle validate -t dev

# Deploy with debug
databricks bundle deploy -t dev --debug
```

### Missing Environment Variables

```bash
# Check required variables
echo $POSTGRES_HOST
echo $AWS_ACCESS_KEY_ID

# Set in .env file or export
export POSTGRES_HOST=your-host.com
```

---

## Project Structure Explained

```
my-data-project/
├── configs/                    # All configuration files
│   ├── pipelines/              # Pipeline definitions (YAML)
│   ├── databricks/             # Databricks job configs
│   └── environments.yaml       # Environment-specific settings
│
├── notebooks/                  # Databricks notebooks
│   └── (add your notebooks here)
│
├── scripts/                    # Utility scripts
│   └── (add helper scripts here)
│
├── tests/                      # Unit and integration tests
│   └── (add tests here)
│
├── docs/                       # Project documentation
│   └── (add documentation here)
│
├── .github/workflows/          # CI/CD workflows
│   └── deploy-dev.yml          # Auto-generated workflow
│
├── databricks.yml              # Databricks Asset Bundle config
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules
└── README.md                   # Project documentation
```

**Where to customize**:
- **Pipeline configs**: `configs/pipelines/*.yaml`
- **Environment settings**: `configs/environments.yaml`
- **Databricks jobs**: `configs/databricks/*.yml`
- **CI/CD**: `.github/workflows/*.yml`

---

## Next Steps

1. **Customize Pipelines** - Edit YAML configs for your data sources
2. **Add Tests** - Create tests in `tests/` directory
3. **Document** - Update `README.md` and add docs in `docs/`
4. **Deploy** - Push to Databricks using Asset Bundles
5. **Monitor** - Query metadata to track pipeline health

---

## Resources

- **KDF GitHub**: https://github.com/shivamwahi2000/kdf
- **Full Documentation**: See KDF `docs/` directory
- **S3 Autoloader**: `docs/S3_AUTOLOADER.md`
- **CI/CD Guide**: `docs/MODERN_CICD.md`
- **Databricks Integration**: `docs/DATABRICKS_INTEGRATION.md`
- **Community Edition Testing**: `examples/community_edition/README.md`

---

## Support

- **Issues**: https://github.com/shivamwahi2000/kdf/issues
- **Discussions**: GitHub Discussions
- **Examples**: KDF `examples/` directory

---

## Summary

**Creating a new data engineering project with KDF**:

```bash
# 1. Install KDF
pip install kdf

# 2. Create project
kdf init project my-data-project
cd my-data-project

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
# Edit .env with your credentials

# 5. Customize pipelines
# Edit configs/pipelines/*.yaml

# 6. Run pipeline
kdf run configs/pipelines/bronze_orders.yaml

# 7. Deploy to Databricks (optional)
databricks bundle deploy -t dev
```

🚀 **You're ready to build production data pipelines!**
