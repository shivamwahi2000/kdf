# KDF Databricks Asset Bundles Resources

This directory contains resource definitions for deploying KDF pipelines using Databricks Asset Bundles (DABs).

## Structure

```
resources/
├── clusters/
│   ├── batch_cluster.yml       # Standard batch processing cluster
│   └── streaming_cluster.yml   # Streaming/realtime cluster with autoscaling
└── jobs/
    ├── single_pipeline_job.yml # Single pipeline template
    ├── medallion_job.yml       # Bronze → Silver → Gold
    └── hybrid_job.yml          # Batch + Streaming combined
```

## Cluster Configurations

### Batch Cluster
- **Purpose**: Bronze/Silver/Gold batch processing
- **Size**: 4 workers (i3.xlarge)
- **Features**: Delta optimizations, Photon, adaptive query execution

### Streaming Cluster
- **Purpose**: Kafka ingestion, streaming transformations
- **Size**: 2-8 workers autoscale (i3.xlarge)
- **Features**: Backpressure, streaming metrics, state store maintenance

## Job Templates

### Single Pipeline Job
Basic template for running a standalone KDF pipeline.

**Usage**:
```yaml
# In your bundle, reference:
resources:
  jobs:
    my_pipeline:
      extends: kdf_single_pipeline
      # Override specific fields
```

### Medallion Job
Complete Bronze → Silver → Gold pipeline with proper dependencies.

**Includes**:
- Bronze: Raw ingestion from source
- Silver: Cleaning, deduplication, validation
- Gold: Business metrics and aggregations

### Hybrid Job
Combines batch historical data with real-time streaming.

**Features**:
- Separate batch and streaming paths
- S3 Autoloader for incremental file ingestion
- Kafka for real-time events
- Combined analytics in Gold layer

## Customizing Jobs

To customize a job for your use case:

1. **Copy the template**:
   ```bash
   cp resources/jobs/medallion_job.yml resources/jobs/my_orders_job.yml
   ```

2. **Update the configuration**:
   ```yaml
   resources:
     jobs:
       my_orders_pipeline:
         name: "My Orders ${var.environment}"
         # Customize tasks, schedules, etc.
   ```

3. **Deploy**:
   ```bash
   databricks bundle deploy -t dev
   ```

## Environment Variables

Jobs use environment-specific variables:

- `${var.environment}` - Current environment (dev/staging/production)
- `${var.config_path}` - Path to pipeline configs
- `${var.metadata_path}` - KDF metadata storage location
- `${var.checkpoint_path}` - Streaming checkpoint location
- `${var.notification_email}` - Email for alerts

These are defined in `databricks.yml` targets.

## Best Practices

1. **Use job cluster keys** - Reference clusters defined in `clusters/`
2. **Set proper timeouts** - 3600s for batch, 0 for streaming
3. **Configure retries** - 2 retries for batch, 0 for streaming
4. **Add libraries** - Always include KDF wheel artifact
5. **Tag resources** - Use tags for cost tracking and organization
6. **Test in dev** - Always deploy to dev before staging/production

## Deployment

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

## Monitoring

After deployment, monitor jobs in Databricks UI:
- Workflows → Find your job
- View run history and logs
- Set up alerts

Query KDF metadata:
```sql
SELECT * FROM delta.`/kdf/metadata/pipeline_runs`
WHERE environment = 'production'
ORDER BY start_time DESC
```
