# Modern CI/CD with Databricks Asset Bundles

## Overview

KDF now uses **Databricks Asset Bundles (DABs)** for modern, production-ready CI/CD. This replaces the legacy Python `databricks-cli` with the new Go-based Databricks CLI and Infrastructure-as-Code approach.

## What Changed

### ❌ Old Approach (Legacy)
- Python `databricks-cli` package
- Manual JSON workflow creation
- `databricks jobs create --json-file`
- No environment management
- No validation before deployment
- Script-based deployment

### ✅ New Approach (Modern)
- New Databricks CLI (Go-based)
- Asset Bundles (Infrastructure-as-Code)
- YAML resource definitions
- Built-in environment management (dev/staging/prod)
- Pre-deployment validation
- Git integration
- Single-command deployment: `databricks bundle deploy -t prod`

---

## Quick Start

### 1. Install New Databricks CLI

```bash
# macOS/Linux
curl -fsSL https://raw.githubusercontent.com/databricks/setup-cli/main/install.sh | sh

# Or download binary
# https://github.com/databricks/cli/releases
```

### 2. Authenticate

```bash
databricks auth login --host https://your-workspace.cloud.databricks.com
```

### 3. Deploy

```bash
# Validate bundle
databricks bundle validate -t dev

# Deploy to dev
databricks bundle deploy -t dev

# Run a job
databricks bundle run -t dev kdf_medallion_orders

# Deploy to production
databricks bundle deploy -t production
```

---

## Bundle Structure

```
kdf/
├── databricks.yml                  # Main bundle config
├── .databricks/
│   └── project.json                # Environment variables
├── resources/
│   ├── clusters/
│   │   ├── batch_cluster.yml       # Batch cluster definition
│   │   └── streaming_cluster.yml   # Streaming cluster definition
│   └── jobs/
│       ├── single_pipeline_job.yml # Single pipeline template
│       ├── medallion_job.yml       # Medallion workflow
│       └── hybrid_job.yml          # Batch + Streaming
└── scripts/
    └── deploy_bundle.sh            # Helper deployment script
```

---

## Environment Configuration

### databricks.yml

Defines the main bundle and targets:

```yaml
bundle:
  name: kdf

targets:
  dev:
    mode: development
    workspace:
      host: ${var.databricks_host_dev}
    variables:
      environment: dev
      config_path: /kdf/configs/dev

  production:
    mode: production
    workspace:
      host: ${var.databricks_host_prod}
    variables:
      environment: production
      config_path: /kdf/configs/production
    run_as:
      service_principal_name: ${var.service_principal_name}
```

### Environment Variables

Set in `.databricks/project.json` or environment:

```json
{
  "version": "2",
  "environments": {
    "dev": {
      "variables": {
        "databricks_host_dev": "${DATABRICKS_HOST_DEV}",
        "notification_email": "${NOTIFICATION_EMAIL_DEV}"
      }
    },
    "production": {
      "variables": {
        "databricks_host_prod": "${DATABRICKS_HOST_PROD}",
        "notification_email": "${NOTIFICATION_EMAIL_PROD}"
      }
    }
  }
}
```

---

## Resource Definitions

### Job Resources (YAML)

Define jobs in `resources/jobs/*.yml`:

```yaml
# resources/jobs/medallion_job.yml
resources:
  jobs:
    kdf_medallion_orders:
      name: "KDF ${var.environment} - Medallion Orders"

      tasks:
        - task_key: bronze_orders
          notebook_task:
            notebook_path: /kdf/notebooks/run_kdf_pipeline
            base_parameters:
              config_path: "${var.config_path}/medallion_orders.yaml"
              config_type: "medallion"
              pipeline_name: "bronze_orders"
          job_cluster_key: kdf_batch_cluster
          libraries:
            - whl: ${workspace.file_path}/artifacts/kdf_wheel/*.whl

        - task_key: silver_orders
          depends_on:
            - task_key: bronze_orders
          # ... more config
```

### Cluster Resources

Define reusable clusters in `resources/clusters/*.yml`:

```yaml
# resources/clusters/batch_cluster.yml
resources:
  job_clusters:
    kdf_batch_cluster:
      new_cluster:
        spark_version: "13.3.x-scala2.12"
        node_type_id: "i3.xlarge"
        num_workers: 4
        runtime_engine: PHOTON
```

---

## Deployment

### Using CLI

```bash
# Development
databricks bundle validate -t dev
databricks bundle deploy -t dev

# Staging
databricks bundle deploy -t staging

# Production (requires approval)
databricks bundle deploy -t production
```

### Using Helper Script

```bash
# Deploy to dev
./scripts/deploy_bundle.sh dev

# Deploy to production
./scripts/deploy_bundle.sh production
```

The script provides:
- ✅ Pre-deployment validation
- ✅ Artifact building (KDF wheel)
- ✅ Deployment plan preview
- ✅ Confirmation prompts
- ✅ Post-deployment summary

---

## CI/CD with GitHub Actions

KDF includes complete GitHub Actions workflows for automated deployment.

### Dev Deployment (Auto on Push)

`.github/workflows/databricks-dev.yml`:

- **Trigger**: Push to `develop` branch
- **Steps**:
  1. Validate bundle
  2. Deploy to dev environment
  3. Run integration tests

### Production Deployment (Manual or Auto)

`.github/workflows/databricks-production.yml`:

- **Trigger**: Push to `main` or manual approval
- **Steps**:
  1. Run unit tests
  2. Validate production bundle
  3. Deploy to staging
  4. Run smoke tests on staging
  5. Deploy to production (with approval)
  6. Create deployment tag
  7. Rollback on failure

### Required GitHub Secrets

```
DATABRICKS_HOST_DEV
DATABRICKS_TOKEN_DEV
NOTIFICATION_EMAIL_DEV

DATABRICKS_HOST_STAGING
DATABRICKS_TOKEN_STAGING
NOTIFICATION_EMAIL_STAGING

DATABRICKS_HOST_PROD
DATABRICKS_TOKEN_PROD
NOTIFICATION_EMAIL_PROD
SERVICE_PRINCIPAL_NAME
```

---

## Key Features

### 1. Environment Isolation

Each environment has:
- Separate workspace paths (`/.bundle/kdf/{environment}`)
- Independent configs (`/kdf/configs/{environment}`)
- Isolated checkpoints (`/kdf/checkpoints/{environment}`)
- Environment-specific variables

### 2. Git Integration

Production deployment tracks Git:
```yaml
git:
  branch: main
  origin_url: https://github.com/shivamwahi2000/kdf.git
```

Resources are version-controlled and synced automatically.

### 3. Pre-deployment Validation

```bash
databricks bundle validate -t production
```

Catches errors before deployment:
- Invalid YAML syntax
- Missing dependencies
- Invalid cluster configurations
- Circular task dependencies

### 4. Artifact Management

Wheel artifacts are built and deployed automatically:
```yaml
artifacts:
  kdf_wheel:
    type: whl
    build: pip wheel . --wheel-dir dist --no-deps
    path: ./dist/*.whl
```

### 5. Service Principal Support

Production uses service principals for security:
```yaml
run_as:
  service_principal_name: ${var.service_principal_name}
```

---

## Migration from Legacy

### Old Way

```bash
# Upload config
kdf databricks upload-config pipeline.yaml

# Create workflow manually
kdf databricks create-workflow pipeline.yaml \
  --config-path dbfs:/kdf/configs/pipeline.yaml

# Or use Python script
python scripts/deploy_to_databricks.py --config pipeline.yaml
```

### New Way

```bash
# Just deploy the bundle
databricks bundle deploy -t dev
```

The bundle includes:
- ✅ Config uploads (automatic)
- ✅ Notebook uploads (automatic)
- ✅ Job creation (declarative)
- ✅ Cluster configuration (reusable)
- ✅ Environment management (built-in)

---

## Best Practices

### 1. Use Targets for Environments

```yaml
targets:
  dev:
    mode: development  # Allows rapid iteration
  production:
    mode: production   # Prevents accidental changes
```

### 2. Parameterize with Variables

```yaml
variables:
  config_path:
    default: /kdf/configs
```

Reference: `${var.config_path}`

### 3. Define Reusable Clusters

Create cluster definitions once, reference everywhere:

```yaml
job_cluster_key: kdf_batch_cluster  # Defined in resources/clusters/
```

### 4. Use Proper Dependencies

```yaml
depends_on:
  - task_key: bronze_orders  # Silver waits for Bronze
```

### 5. Tag Resources

```yaml
tags:
  framework: kdf
  environment: ${var.environment}
  cost_center: analytics
```

### 6. Test in Dev First

```bash
# Always validate and test in dev
databricks bundle validate -t dev
databricks bundle deploy -t dev
databricks bundle run -t dev kdf_medallion_orders

# Then promote to production
databricks bundle deploy -t production
```

---

## Monitoring

### View Deployed Resources

```bash
# List bundle resources
databricks bundle summary -t production

# List deployed jobs
databricks jobs list --output json | \
  jq '.jobs[] | select(.settings.name | contains("KDF production"))'
```

### Check Deployment Status

```bash
# View workspace bundle
databricks workspace ls /.bundle/kdf/production

# View job runs
databricks runs list --job-id <job_id>
```

### Query Metadata

```sql
SELECT
  pipeline_name,
  environment,
  status,
  records_written,
  start_time
FROM delta.`/kdf/metadata/pipeline_runs`
WHERE environment = 'production'
  AND DATE(start_time) = CURRENT_DATE()
ORDER BY start_time DESC;
```

---

## Troubleshooting

### Bundle Validation Fails

```bash
databricks bundle validate -t dev
```

Common issues:
- **Invalid YAML**: Check syntax with `yamllint`
- **Missing variables**: Set in `.databricks/project.json`
- **Circular dependencies**: Review `depends_on` in tasks

### Deployment Fails

```bash
databricks bundle deploy -t dev --debug
```

Check:
- Workspace permissions
- Service principal credentials
- Network connectivity

### Job Fails After Deployment

1. Check job run logs in Databricks UI
2. Verify KDF wheel is installed
3. Check config file exists in DBFS
4. Query metadata for error details

---

## Advanced Usage

### Custom Resource Types

Add other Databricks resources:

```yaml
resources:
  pipelines:
    my_dlt_pipeline:
      # Delta Live Tables definition

  mlflow_experiments:
    my_experiment:
      # MLflow experiment config
```

### Dynamic Configuration

Use Databricks secrets:

```yaml
variables:
  db_password:
    lookup:
      secret_scope: kdf-secrets
      secret_key: postgres-password
```

### Multi-Region Deployment

```yaml
targets:
  us_east:
    workspace:
      host: https://workspace-us-east.cloud.databricks.com

  eu_west:
    workspace:
      host: https://workspace-eu-west.cloud.databricks.com
```

---

## Comparison: Legacy vs Modern

| Feature | Legacy (databricks-cli) | Modern (Asset Bundles) |
|---------|-------------------------|------------------------|
| CLI | Python package | Go binary |
| Configuration | JSON | YAML |
| Environments | Manual | Built-in (dev/staging/prod) |
| Validation | None | `bundle validate` |
| Deployment | Multi-step scripts | Single command |
| Git Integration | Manual | Automatic |
| Rollback | Manual | Supported |
| State Management | None | Automatic |
| Resource Reuse | Copy-paste | Shared definitions |
| Testing | Manual | CI/CD integrated |

---

## Summary

KDF now uses **Databricks Asset Bundles** for:

✅ **Modern Infrastructure-as-Code** - YAML-based resource definitions
✅ **Environment Management** - Dev/staging/prod isolation
✅ **Single-Command Deployment** - `databricks bundle deploy`
✅ **Pre-deployment Validation** - Catch errors before deploy
✅ **Git Integration** - Version-controlled resources
✅ **Service Principal Support** - Production security
✅ **CI/CD Ready** - GitHub Actions workflows included
✅ **Backward Compatible** - Legacy scripts still available

**Deploy with confidence:**
```bash
databricks bundle deploy -t production
```

---

## Resources

- **Databricks Asset Bundles Docs**: https://docs.databricks.com/dev-tools/bundles/
- **New Databricks CLI**: https://github.com/databricks/cli
- **Setup Guide**: https://docs.databricks.com/dev-tools/cli/install.html
- **Bundle Reference**: https://docs.databricks.com/dev-tools/bundles/reference.html

---

**Next**: See [S3_AUTOLOADER.md](./S3_AUTOLOADER.md) for modern S3 ingestion
