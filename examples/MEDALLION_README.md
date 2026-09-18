# Medallion Architecture Examples

These examples demonstrate KDF's hybrid architecture support: Medallion as the foundation with streaming capabilities where needed.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                   GOLD LAYER                            │
│         (Business Metrics & Aggregations)               │
│  • Daily revenue                                        │
│  • User activity metrics                                │
│  • Execution: Batch (daily/hourly)                      │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│                  SILVER LAYER                           │
│         (Cleaned, Validated, Deduplicated)              │
│  • Orders (validated)                                   │
│  • Clickstream (processed)                              │
│  • Execution: Batch or Micro-batch                      │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│                  BRONZE LAYER                           │
│              (Raw Ingestion)                            │
│  • Orders from Postgres (incremental, batch)            │
│  • Clickstream from Kafka (streaming)                   │
│  • Execution: Batch or Streaming                        │
└─────────────────────────────────────────────────────────┘
```

## Examples

### 1. Basic Medallion (Batch Only)

**File**: `medallion_orders.yaml`

**Architecture**:
```
PostgreSQL → Bronze → Silver → Gold
  (batch)    (raw)   (clean)  (metrics)
```

**Layers**:
- **Bronze**: Raw orders from PostgreSQL, incremental ingestion
- **Silver**: Deduplicated and validated orders
- **Gold**: Daily revenue metrics aggregated by customer

**Run**:
```bash
kdf validate-medallion examples/medallion_orders.yaml
kdf run-medallion examples/medallion_orders.yaml
```

**Use Case**: Standard data warehouse ETL

---

### 2. Hybrid (Batch + Streaming)

**File**: `hybrid_clickstream.yaml`

**Architecture**:
```
Batch Path:     PostgreSQL → Bronze → Silver → Gold
                  (hourly)

Streaming Path: Kafka → Bronze → Silver
                  (real-time, 5-min micro-batch)

Combined:       Both Silver layers → Gold analytics
```

**Layers**:
- **Bronze (Batch)**: Historical orders from PostgreSQL
- **Bronze (Streaming)**: Real-time clickstream from Kafka
- **Silver**: Processed and validated data from both sources
- **Gold**: Combined analytics

**Run**:
```bash
kdf validate-medallion examples/hybrid_clickstream.yaml
kdf run-medallion examples/hybrid_clickstream.yaml
```

**Use Case**: Combines batch historical data with real-time event streams

---

## Key Features Demonstrated

### 1. Execution Modes

```yaml
execution_mode: batch          # Traditional batch processing
execution_mode: micro_batch    # 5-15 minute micro-batches
execution_mode: streaming      # True real-time streaming
```

### 2. Medallion Layers

```yaml
medallion:
  layer: bronze|silver|gold|custom
  upstream_layers: [bronze]
  quality_level: raw|validated|enriched
  description: Layer description
```

### 3. Pipeline Dependencies

```yaml
depends_on: [bronze_orders, bronze_clickstream]
```

KDF automatically:
- Validates dependencies form a DAG
- Computes execution order
- Runs pipelines in correct sequence
- Allows parallel execution where possible

### 4. Delta Lake Integration

All layers use Delta Lake:
- ACID transactions
- Time travel
- Schema evolution
- Efficient updates

### 5. Streaming Configuration

```yaml
execution_mode: streaming
trigger: "5 minutes"
checkpoint_location: /checkpoints/my_pipeline
```

---

## When to Use Each Mode

### Batch Mode
✅ Historical data loads
✅ Daily/hourly aggregations
✅ Data that doesn't require real-time
✅ Most analytics use cases (90%)

**Latency**: Minutes to hours

### Micro-Batch Mode
✅ Near real-time dashboards
✅ 5-15 minute refresh requirements
✅ Balance between latency and cost
✅ Most "real-time" requirements (8%)

**Latency**: 5-15 minutes

### Streaming Mode
✅ True real-time alerts
✅ Sub-minute latency required
✅ Event-driven systems
✅ High-frequency data sources (2%)

**Latency**: Seconds to minutes

---

## Execution

### Validate Configuration

```bash
kdf validate-medallion medallion_orders.yaml
```

Output:
```
✓ Configuration valid: medallion_orders.yaml

Workflow: orders_medallion
Pipelines: 3

Execution order (3 stages):
  Stage 1: bronze_orders
  Stage 2: silver_orders
  Stage 3: gold_daily_revenue

Medallion Layers:
  BRONZE: bronze_orders
  SILVER: silver_orders
  GOLD: gold_daily_revenue
```

### Run Workflow

```bash
kdf run-medallion medallion_orders.yaml
```

Output:
```
Medallion Workflow: orders_medallion
Pipelines: 3

Execution Plan (3 stages):
  Stage 1: bronze_orders
  Stage 2: silver_orders
  Stage 3: gold_daily_revenue

Starting execution...

Stage 1/3: bronze_orders
  → bronze_orders (bronze layer)
    ✓ Status: SUCCESS
    ✓ Records read: 125,847
    ✓ Records written: 125,847

Stage 2/3: silver_orders
  → silver_orders (silver layer)
    ✓ Status: SUCCESS
    ✓ Records read: 125,847
    ✓ Records written: 124,005

Stage 3/3: gold_daily_revenue
  → gold_daily_revenue (gold layer)
    ✓ Status: SUCCESS
    ✓ Records read: 124,005
    ✓ Records written: 12,458

✓ Medallion workflow completed successfully!
```

---

## Configuration Tips

### 1. Start Simple

Begin with batch-only Bronze → Silver:
```yaml
pipelines:
  - name: bronze
    source: { type: postgres }
    target: { path: /bronze }

  - name: silver
    depends_on: [bronze]
    source: { type: delta, path: /bronze }
    skills: [deduplicate]
    target: { path: /silver }
```

### 2. Add Gold Layer

Once Silver is stable:
```yaml
  - name: gold
    depends_on: [silver]
    source: { type: delta, path: /silver }
    skills:
      - aggregate: { group_by: [date], metrics: [...] }
    target: { path: /gold }
```

### 3. Add Streaming

Only for sources that need it:
```yaml
  - name: bronze_realtime
    execution_mode: streaming
    trigger: "5 minutes"
    source: { type: kafka }
    target: { path: /bronze }
```

---

## Best Practices

### Layer Responsibilities

**Bronze**:
- Raw ingestion only
- No transformations
- Preserve everything
- Source of truth

**Silver**:
- Clean and validate
- Deduplicate
- Schema evolution
- Ready for analytics

**Gold**:
- Business metrics
- Aggregations
- Optimized for queries
- Specific use cases

### Execution Frequency

**Bronze**: As often as source updates (hourly, real-time)
**Silver**: Slightly less frequent (hourly, 15-min)
**Gold**: Business cadence (daily, hourly)

### Partitioning

- **Bronze**: By ingestion_date
- **Silver**: By business_date
- **Gold**: By business dimension (date, customer, etc.)

---

## Monitoring

Use KDF metadata to monitor health:

```bash
# Check status
kdf status

# View history
kdf history bronze_orders
kdf history silver_orders
kdf history gold_daily_revenue
```

Query metadata directly:
```sql
SELECT
  pipeline_name,
  medallion_layer,
  status,
  records_written,
  execution_time
FROM kdf_pipeline_runs
WHERE run_date = current_date()
ORDER BY start_time
```

---

## Troubleshooting

### Pipeline Failed

1. Check which layer failed
2. Inspect that layer's Bronze data
3. Review quality check violations
4. Fix upstream data or adjust validation

### Slow Performance

1. Check partition strategy
2. Review aggregation complexity
3. Consider micro-batch instead of batch
4. Optimize Spark configuration

### Data Missing

1. Check Bronze layer first
2. Verify source connectivity
3. Review incremental watermarks
4. Check quality check filters

---

## Next Steps

1. Start with basic medallion (batch only)
2. Add Gold layer for metrics
3. Introduce streaming for specific sources
4. Monitor and optimize
5. Extend with custom skills

---

**Remember**: Most use cases don't need streaming. Start with batch, add streaming only where justified by business requirements and latency SLAs.
