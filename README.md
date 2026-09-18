# KDF — Krianno Data Framework

**Build the foundation for an Agentic Data Engineering Ecosystem**

KDF is a production-minded framework that provides reusable, composable data engineering primitives designed to be used by both human engineers and AI agents.

## What is KDF?

KDF solves a fundamental problem: modern data engineering requires repeatedly implementing the same patterns across different projects:

- ✓ Connect to data sources securely
- ✓ Implement incremental processing
- ✓ Handle schema changes
- ✓ Deduplicate records
- ✓ Implement data quality checks
- ✓ Monitor pipeline health
- ✓ Debug failed pipelines

Instead of reinventing these patterns, KDF provides battle-tested primitives that can be composed into reliable data pipelines.

**Crucially, KDF is designed for an agentic future**: AI coding agents can use KDF's skills, tools, and structured metadata to build, operate, debug, and optimize data systems.

## Key Features

### For Data Engineers

- **Declarative Pipelines**: Define pipelines in simple YAML
- **Built-in Skills**: Incremental ingestion, deduplication, quality checks, schema evolution
- **Production Ready**: Databricks/Spark native, Delta Lake support, comprehensive metadata
- **Extensible**: Clean SDK for custom connectors and skills

### For AI Agents

- **Agent Skills**: Portable skill specifications for common data engineering tasks
- **Structured Metadata**: Queryable Delta-backed metadata for investigation and analysis
- **Tools Registry**: Standardized tools for pipeline inspection and debugging
- **Deterministic Operations**: Predictable, well-documented behavior

## Quick Start

### Installation

```bash
pip install kdf
```

### Initialize a Project

```bash
kdf init
```

This creates:
- `pipeline.yaml` - Example pipeline configuration
- `.env.template` - Environment variables template

### Configure Environment

```bash
cp .env.template .env
# Edit .env with your credentials
```

### Define a Pipeline

Create `pipeline.yaml`:

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

### Run the Pipeline

```bash
# Validate configuration
kdf validate pipeline.yaml

# Run pipeline
kdf run pipeline.yaml

# Check status
kdf status

# View history
kdf history orders_ingestion
```

## Architecture

KDF is built around composable layers:

```
┌─────────────────────────────────────┐
│           Connectors                │
│  PostgreSQL │ S3 │ (Extensible)     │
└─────────────────────────────────────┘
               ↓
┌─────────────────────────────────────┐
│          Data Skills                │
│  Ingestion │ Quality │ Transform    │
└─────────────────────────────────────┘
               ↓
┌─────────────────────────────────────┐
│           Runtime                   │
│       Databricks / PySpark          │
└─────────────────────────────────────┘
               ↓
┌─────────────────────────────────────┐
│          Metadata Layer             │
│    Delta-backed, Queryable          │
└─────────────────────────────────────┘
               ↓
┌─────────────────────────────────────┐
│         Agent Skills                │
│  Builder │ Debugger │ Investigator  │
└─────────────────────────────────────┘
```

## Connectors (v0.1)

- **PostgreSQL**: Full and incremental loads via JDBC
- **S3**: CSV, JSON, JSONL, Parquet

## Data Skills (v0.1)

### Ingestion
- `full_load`: Complete dataset refresh
- `incremental`: Watermark-based incremental processing

### Transformation
- `deduplicate`: Remove duplicate records with configurable keys

### Quality
- `not_null`: Validate required fields
- `unique`: Check for duplicates
- `freshness`: Ensure data is recent

### Schema
- `schema_evolution`: Detect and handle schema changes

### Reconciliation
- `reconcile`: Compare source and target record counts

## Agent Skills (v0.1)

Agent Skills are specifications that guide AI coding agents in performing data engineering tasks:

- **pipeline-builder**: Generate KDF pipeline configurations from requirements
- **pipeline-debugger**: Investigate failed pipelines and identify root causes
- **data-quality-investigator**: Analyze quality check failures
- **spark-optimizer**: Identify performance bottlenecks
- **dataset-documenter**: Generate dataset documentation

See `kdf/agents/skills/*/SKILL.md` for detailed specifications.

## Tools for Agents

KDF provides tools that agents can use to interact with pipelines:

- `inspect_pipeline_run`: Get detailed run information
- `inspect_pipeline_history`: View execution history
- `query_metadata`: SQL queries against metadata
- `inspect_schema`: Examine dataset schemas
- `compare_schema`: Detect schema differences

## Example Pipelines

### Incremental PostgreSQL → Delta

```yaml
name: customer_events

source:
  type: postgres
  connection: app_db
  table: events

ingestion:
  skill: incremental
  column: created_at

skills:
  - deduplicate:
      keys: [event_id]

quality:
  - not_null:
      columns: [event_id, user_id]
  - freshness:
      column: created_at
      threshold: 6h

target:
  type: delta
  path: /data/events
  partition_by: [event_date]
```

### S3 Parquet → Delta

```yaml
name: transaction_load

source:
  type: s3
  path: s3://data-lake/transactions/
  format: parquet

skills:
  - deduplicate:
      keys: [transaction_id]
      order_by: updated_at

quality:
  - unique:
      columns: [transaction_id]

target:
  type: delta
  path: /data/transactions
  mode: append
```

## Development

### Run Tests

```bash
pytest
```

### Install Development Dependencies

```bash
pip install -e ".[dev]"
```

### Code Quality

```bash
black kdf/
ruff check kdf/
mypy kdf/
```

## Roadmap

See [docs/vision.md](docs/vision.md) for the long-term vision.

### v0.1 (Current)
- ✓ Core architecture
- ✓ PostgreSQL and S3 connectors
- ✓ Essential data skills
- ✓ Metadata layer
- ✓ Agent skills foundation
- ✓ CLI

### v0.2 (Planned)
- More connectors (Snowflake, BigQuery, APIs)
- More data skills (SCD Type 2, CDC)
- Enhanced schema management
- Improved observability
- Agent skill marketplace foundation

### v1.0 (Future)
- Full agent skill ecosystem
- Third-party connector registry
- Advanced orchestration integration
- Enterprise features

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

KDF welcomes contributions:
- New connectors
- New data skills
- Agent skills
- Documentation improvements
- Bug fixes

## Documentation

- [Vision](docs/vision.md) - Long-term vision for KDF
- [Ecosystem](docs/ecosystem.md) - Future ecosystem architecture
- [Examples](examples/) - Example pipelines and use cases

## License

Apache License 2.0 - See [LICENSE](LICENSE)

## Credits

Built by Krianno TechLabs

---

**KDF — Don't make the agent reinvent data engineering. Give it reusable skills.**
