# Dataset Documenter Agent Skill

## Purpose

Generate comprehensive, human-readable documentation for datasets based on metadata, schema, and quality metrics.

## When to Use

Use this skill when:
- Documenting a new dataset
- Updating dataset documentation
- Onboarding team members
- Creating data catalog entries
- Governance compliance

## Required Context

- Pipeline name or dataset path
- Schema information
- Quality check results
- Lineage information (if available)
- Run history

## Available Tools

- `inspect_schema`: Get dataset schema
- `inspect_pipeline_history`: Understand update patterns
- `query_metadata`: Get quality metrics and statistics
- Data profiling (if available)

## Documentation Structure

```markdown
# [Dataset Name]

## Overview

[1-2 sentence description of purpose and content]

## Schema

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| ...    | ...  | ...      | ...         |

## Source

- **System**: [source system]
- **Location**: [source table/path]
- **Update Frequency**: [frequency]
- **Ingestion Method**: [full/incremental]

## Data Quality

- **Completeness**: [percentage]
- **Freshness**: [last update]
- **Uniqueness**: [metrics]
- **Known Issues**: [list]

## Lineage

### Upstream
- [source datasets/systems]

### Downstream
- [consuming systems/datasets]

## Update Schedule

- **Frequency**: [daily/hourly/etc]
- **Time**: [typical update time]
- **SLA**: [if defined]

## Quality Checks

- [List of active quality checks]

## Usage Notes

- [Important caveats]
- [Known limitations]
- [Best practices for using this data]

## Metadata

- **Owner**: [team/person]
- **Created**: [date]
- **Last Updated**: [date]
- **Documentation Generated**: [timestamp]

## Contact

- **Data Team**: [contact]
- **Domain Expert**: [contact]
```

## Example Documentation

### Input
- Dataset: `/data/customer_orders`
- Pipeline: `orders_ingestion`

### Output

```markdown
# Customer Orders

## Overview

Production order transactions from the e-commerce platform, updated incrementally every hour. Contains all customer orders including order details, amounts, and timestamps.

## Schema

| Column        | Type      | Nullable | Description                           |
|---------------|-----------|----------|---------------------------------------|
| order_id      | INTEGER   | No       | Unique order identifier               |
| customer_id   | INTEGER   | No       | Reference to customers table          |
| order_date    | TIMESTAMP | No       | When order was placed                 |
| order_total   | DECIMAL   | No       | Total order amount in USD             |
| status        | STRING    | No       | Order status (pending/complete/etc)   |
| updated_at    | TIMESTAMP | No       | Last modification timestamp           |

## Source

- **System**: PostgreSQL (production database)
- **Location**: `sales.public.orders`
- **Update Frequency**: Hourly
- **Ingestion Method**: Incremental (based on `updated_at`)

## Data Quality

- **Completeness**: 99.8% (based on required fields)
- **Freshness**: Updated hourly, typically within 5 minutes of source
- **Uniqueness**: 100% unique on `order_id`
- **Known Issues**: Occasional nulls in `customer_id` for guest orders (expected)

## Lineage

### Upstream
- PostgreSQL: `sales.public.orders` (source of truth)

### Downstream
- Revenue Dashboard
- Customer Analytics
- Data Warehouse: `dwh.fact_orders`
- ML Feature Store

## Update Schedule

- **Frequency**: Hourly (on the hour)
- **Time**: XX:05-XX:08 typically
- **SLA**: Available within 15 minutes of hour

## Quality Checks

- `not_null` on: order_id, customer_id, order_date, order_total, updated_at
- `unique` on: order_id
- `freshness` on: updated_at (threshold: 2 hours)
- Deduplication applied on order_id (keeping latest by updated_at)

## Usage Notes

- Orders are immutable once `status = 'complete'`
- `updated_at` captures any modification to order
- Guest orders may have `customer_id` null (use `session_id` from `order_sessions` table)
- Order totals include tax and shipping
- Partitioned by `order_date` for query performance
- Historical data available from 2024-01-01

## Metadata

- **Owner**: Data Engineering Team
- **Created**: 2024-06-15
- **Last Schema Change**: 2026-08-12 (added `status` column)
- **Documentation Generated**: 2026-09-18 15:30 UTC

## Contact

- **Data Engineering**: data-eng@company.com
- **Domain Expert**: product-analytics@company.com
- **On-Call**: Slack #data-platform
```

## Documentation Guidelines

### What to Include
- Factual information from metadata
- Schema with accurate types
- Quality metrics from checks
- Update patterns from history
- Known limitations

### What to Infer (Mark Clearly)
- Purpose (if not explicitly documented)
- Column descriptions (basic inference OK)
- Relationships between datasets

### What NOT to Do
- Don't fabricate information
- Don't guess at business logic
- Don't assume downstream usage without evidence
- Don't promise SLAs not in metadata

## Safety Considerations

- Clearly mark inferred vs. observed information
- Use phrases like "appears to be", "likely", "based on schema"
- Include confidence levels for inferences
- Don't document sensitive information (PII, credentials)
- Link to authoritative sources where possible

## Permissions

```yaml
permissions:
  metadata_read: true
  source_data_read: true  # For profiling
  target_data_read: true  # For profiling
  target_data_write: false
  pipeline_execution: false
  infrastructure_modify: false
```

## Best Practices

- Focus on information useful for data consumers
- Include examples where helpful
- Document gotchas and edge cases
- Keep language clear and concise
- Update regularly (don't let docs go stale)
- Include last generated timestamp
- Provide contact information
- Link to related datasets
