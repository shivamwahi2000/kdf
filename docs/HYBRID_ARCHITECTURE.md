# KDF Hybrid Architecture Guide

## Overview

KDF implements a **hybrid architecture** that combines the best of three patterns:

- **Medallion Architecture** (Foundation): Bronze → Silver → Gold layers
- **Batch Processing** (Default): Efficient, cost-effective, proven
- **Streaming Processing** (Where Needed): Real-time for specific use cases

## Architecture Philosophy

### The 90-8-2 Rule

- **90% of data**: Batch processing (hourly/daily) is sufficient
- **8% of data**: Micro-batch (5-15 minutes) meets requirements
- **2% of data**: True streaming (sub-minute) is actually needed

**Don't over-engineer for the 2%.**

### Hybrid Approach

```
Medallion Layers (Structure)
     ×
Execution Modes (Speed)
     =
Hybrid Architecture (Flexibility)
```

---

## Medallion Architecture

### Layer Responsibilities

#### Bronze Layer (Raw)
**Purpose**: Preserve source data exactly as received

**Characteristics**:
- No transformations
- All records preserved
- Source of truth
- Immutable history

**Example**:
```yaml
- name: bronze_orders
  medallion:
    layer: bronze
    quality_level: raw

  source:
    type: postgres
    table: orders

  ingestion:
    skill: incremental
    column: updated_at

  target:
    path: /medallion/bronze/orders
```

#### Silver Layer (Refined)
**Purpose**: Clean, validate, and standardize data

**Characteristics**:
- Deduplicated
- Validated (quality checks)
- Schema standardized
- Ready for analytics

**Example**:
```yaml
- name: silver_orders
  depends_on: [bronze_orders]

  medallion:
    layer: silver
    upstream_layers: [bronze]
    quality_level: validated

  source:
    type: delta
    path: /medallion/bronze/orders

  skills:
    - deduplicate:
        keys: [order_id]
    - schema_evolution:
        mode: compatible

  quality:
    - not_null:
        columns: [order_id, customer_id]
    - unique:
        columns: [order_id]

  target:
    path: /medallion/silver/orders
```

#### Gold Layer (Business)
**Purpose**: Create business-specific metrics and aggregations

**Characteristics**:
- Aggregated
- Business logic applied
- Optimized for queries
- Use-case specific

**Example**:
```yaml
- name: gold_daily_revenue
  depends_on: [silver_orders]

  medallion:
    layer: gold
    upstream_layers: [silver]
    quality_level: enriched

  source:
    type: delta
    path: /medallion/silver/orders

  skills:
    - aggregate:
        group_by: [order_date, customer_id]
        metrics:
          - name: total_revenue
            agg: sum
            column: amount
          - name: order_count
            agg: count

  target:
    path: /medallion/gold/daily_revenue
```

---

## Execution Modes

### 1. Batch Mode (Default)

**Use For**:
- Historical loads
- Daily/hourly processing
- 90% of analytics use cases

**Characteristics**:
- Scheduled execution
- Complete dataset processing
- Cost-effective
- Simple to maintain

**Configuration**:
```yaml
execution_mode: batch
```

**Latency**: Minutes to hours

**Example Schedule**:
- Bronze: Every hour
- Silver: Every hour (after Bronze)
- Gold: Once per day

---

### 2. Micro-Batch Mode

**Use For**:
- Near real-time dashboards
- 5-15 minute refresh requirements
- Most "real-time" business needs

**Characteristics**:
- Triggered on schedule
- Processes recent changes
- Balance of latency and cost
- Structured Streaming

**Configuration**:
```yaml
execution_mode: micro_batch
trigger: "5 minutes"
checkpoint_location: /checkpoints/my_pipeline
```

**Latency**: 5-15 minutes

**Example Use Cases**:
- Real-time dashboards
- Operational monitoring
- Customer activity tracking

---

### 3. Streaming Mode

**Use For**:
- True real-time requirements
- Sub-minute latency
- Event-driven systems
- Only when business justifies complexity and cost

**Characteristics**:
- Continuous processing
- Event-by-event or micro-batch
- Higher complexity
- Higher cost

**Configuration**:
```yaml
execution_mode: streaming
trigger: "10 seconds"
checkpoint_location: /checkpoints/my_pipeline

source:
  type: kafka
  bootstrap_servers: kafka:9092
  topic: events
```

**Latency**: Seconds

**Example Use Cases**:
- Fraud detection
- Real-time alerting
- High-frequency trading
- IoT sensor processing

---

## Hybrid Patterns

### Pattern 1: Batch Medallion (Most Common)

```
PostgreSQL
    ↓ (batch, hourly)
Bronze Layer
    ↓ (batch, hourly)
Silver Layer
    ↓ (batch, daily)
Gold Layer
```

**Use Case**: Traditional data warehouse

**Configuration**:
```yaml
name: batch_medallion
pipelines:
  - bronze: { execution_mode: batch }
  - silver: { execution_mode: batch, depends_on: [bronze] }
  - gold: { execution_mode: batch, depends_on: [silver] }
```

---

### Pattern 2: Hot + Cold Path

```
PostgreSQL (Historical)
    ↓ (batch, daily)
Bronze (Batch)
    ↓
Silver (Batch) ──┐
                 ├─→ Gold (Combined Analytics)
Kafka (Real-time) │
    ↓ (streaming)  │
Bronze (Stream) ──┘
    ↓
Silver (Stream) ──┘
```

**Use Case**: Combine historical + real-time data

**Configuration**:
```yaml
name: hot_cold_path
pipelines:
  # Cold path (batch)
  - bronze_batch: { source: postgres, execution_mode: batch }
  - silver_batch: { source: bronze_batch, execution_mode: batch }

  # Hot path (streaming)
  - bronze_stream: { source: kafka, execution_mode: streaming }
  - silver_stream: { source: bronze_stream, execution_mode: micro_batch }

  # Combined gold
  - gold: { depends_on: [silver_batch, silver_stream] }
```

---

### Pattern 3: Lambda-like (Advanced)

```
Source
  ├─→ Batch Layer (Historical) ──┐
  │                               ├─→ Serving Layer
  └─→ Speed Layer (Real-time) ───┘
```

**Use Case**: Complex requirements with both batch and streaming

**Note**: Only use if absolutely necessary. Medallion hybrid is simpler for most cases.

---

## Connectors by Mode

### Batch Connectors
- ✅ PostgreSQL
- ✅ S3
- ✅ Delta Lake
- ✅ Any JDBC source

### Streaming Connectors
- ✅ Kafka
- ✅ Delta Lake (as stream)
- ⏳ Kinesis (future)
- ⏳ Event Hubs (future)

---

## Multi-Pipeline Configuration

### Dependencies

```yaml
name: my_workflow
pipelines:
  - name: pipeline_a
    # No dependencies

  - name: pipeline_b
    depends_on: [pipeline_a]  # Runs after A

  - name: pipeline_c
    depends_on: [pipeline_a]  # Also runs after A (parallel with B)

  - name: pipeline_d
    depends_on: [pipeline_b, pipeline_c]  # Runs after both B and C
```

**Execution Order** (automatically computed):
```
Stage 1: pipeline_a
Stage 2: pipeline_b, pipeline_c (parallel)
Stage 3: pipeline_d
```

### Validation

KDF validates:
- ✅ All dependencies exist
- ✅ No circular dependencies
- ✅ Valid DAG structure

### Parallel Execution

Pipelines in the same stage can run in parallel (future feature):
```bash
kdf run-medallion config.yaml --parallel
```

---

## Configuration Reference

### Complete Pipeline Config

```yaml
name: pipeline_name

# Execution configuration
execution_mode: batch|micro_batch|streaming
trigger: "5 minutes"  # For micro_batch or streaming
checkpoint_location: /checkpoints/path  # For streaming

# Medallion configuration
medallion:
  layer: bronze|silver|gold|custom
  upstream_layers: [bronze]
  quality_level: raw|validated|enriched
  description: "Layer description"

# Dependencies
depends_on: [other_pipeline1, other_pipeline2]

# Source
source:
  type: postgres|s3|delta|kafka
  # ... connector-specific config

# Ingestion
ingestion:
  skill: full_load|incremental
  column: updated_at  # For incremental

# Skills
skills:
  - deduplicate: { keys: [id] }
  - aggregate: { group_by: [date], metrics: [...] }
  - schema_evolution: { mode: compatible }

# Quality
quality:
  - not_null: { columns: [...] }
  - unique: { columns: [...] }
  - freshness: { column: date, threshold: 24h }

# Target
target:
  type: delta
  path: /path/to/data
  mode: append|overwrite
  partition_by: [date]
```

---

## CLI Commands

### Single Pipeline

```bash
# Traditional single pipeline
kdf validate pipeline.yaml
kdf run pipeline.yaml
```

### Multi-Pipeline (Medallion)

```bash
# Validate medallion workflow
kdf validate-medallion medallion.yaml

# Run medallion workflow
kdf run-medallion medallion.yaml

# Run with parallel execution (future)
kdf run-medallion medallion.yaml --parallel
```

---

## Best Practices

### 1. Start Batch

Always start with batch mode:
```yaml
execution_mode: batch
```

Only move to micro-batch/streaming if:
- Business has documented latency requirement
- SLA demands it
- Cost is justified

### 2. Layer Separation

Keep layers focused:
- Bronze: Ingestion only
- Silver: Cleaning and validation
- Gold: Business logic

### 3. Progressive Enhancement

```
Week 1: Bronze (batch)
Week 2: Silver (batch)
Week 3: Gold (batch)
Week 4: Add streaming to Bronze (if needed)
Week 5: Add micro-batch to Silver (if needed)
```

### 4. Monitor Everything

Track metrics at each layer:
- Record counts
- Processing time
- Quality violations
- Latency

### 5. Test in Layers

Test each layer independently:
```bash
kdf run bronze.yaml
# Verify Bronze data

kdf run silver.yaml
# Verify Silver data

kdf run gold.yaml
# Verify Gold data
```

---

## Migration Guide

### From Single Pipeline to Medallion

**Before**:
```yaml
name: orders
source: { type: postgres }
target: { path: /data/orders }
```

**After**:
```yaml
name: orders_medallion
pipelines:
  - name: bronze
    source: { type: postgres }
    target: { path: /bronze/orders }

  - name: silver
    depends_on: [bronze]
    source: { type: delta, path: /bronze/orders }
    target: { path: /silver/orders }
```

### Adding Streaming

**Start**: Batch Bronze
```yaml
- name: bronze
  execution_mode: batch
  source: { type: postgres }
```

**Add**: Streaming Bronze
```yaml
- name: bronze_stream
  execution_mode: streaming
  source: { type: kafka }
  target: { path: /bronze/stream }
```

**Combine**: In Silver
```yaml
- name: silver
  depends_on: [bronze, bronze_stream]
  # Process both sources
```

---

## Performance Tuning

### Batch Optimization
- Partition appropriately
- Use incremental loading
- Optimize Spark configuration
- Cache intermediate results

### Streaming Optimization
- Tune trigger intervals
- Configure checkpointing
- Monitor lag
- Scale resources appropriately

### Micro-Batch Sweet Spot
- 5-15 minute triggers
- Balance latency vs. cost
- Most "real-time" needs satisfied

---

## Troubleshooting

### Pipeline Dependencies

**Problem**: Circular dependency
```
✗ Circular dependency detected among pipelines: [A, B, C]
```

**Solution**: Review dependency graph, remove cycle

### Streaming Issues

**Problem**: Checkpoint corruption
**Solution**: Delete checkpoint, restart from specific offset

**Problem**: Lag building up
**Solution**: Increase resources, tune trigger interval

### Layer Issues

**Problem**: Silver has more records than Bronze
**Solution**: Check deduplication logic, verify incremental

---

## Summary

KDF's hybrid architecture gives you:

✅ **Structure**: Medallion layers (Bronze/Silver/Gold)
✅ **Flexibility**: Choose execution mode per pipeline
✅ **Simplicity**: Batch by default
✅ **Power**: Streaming where needed
✅ **Safety**: Dependencies and validation
✅ **Observability**: Metadata at every layer

**Start simple. Add complexity only when justified.**

---

**Next Steps**:
1. Try batch medallion example
2. Add Gold layer
3. Introduce streaming only if needed
4. Monitor and optimize
5. Scale confidently

For examples, see `examples/MEDALLION_README.md`
