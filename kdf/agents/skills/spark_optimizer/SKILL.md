# Spark Optimizer Agent Skill

## Purpose

Analyze Databricks/Spark pipeline performance and identify optimization opportunities.

## When to Use

Use this skill when:
- Pipeline is running slowly
- Performance has degraded
- Resource usage is high
- Optimizing new pipelines
- Cost reduction efforts

## Required Context

- Pipeline name
- Run IDs (especially slow runs)
- Execution times
- Data volumes
- Available Spark UI metrics (if accessible)

## Available Tools

- `inspect_pipeline_run`: Get execution metadata
- `inspect_pipeline_history`: Analyze performance trends
- `query_metadata`: Get historical metrics
- `inspect_schema`: Check data types and structure

## Analysis Areas

### 1. Data Skew
- Uneven partition distribution
- Hot partitions
- Stragglers in execution

### 2. Shuffle Operations
- Excessive shuffles
- Large shuffle sizes
- Unnecessary repartitioning

### 3. File Sizing
- Too many small files
- Files too large
- Suboptimal partitioning

### 4. Schema Issues
- Wide schemas
- Inefficient data types
- Unnecessary columns

### 5. Joins
- Join strategies
- Broadcast opportunities
- Key distribution

### 6. Caching
- Missing cache opportunities
- Over-caching
- Cache eviction

## Output Format

```markdown
## PERFORMANCE ANALYSIS

Pipeline: [name]
Analyzed runs: [run IDs]
Current duration: [time]
Data volume: [records/GB]

## OBSERVED BOTTLENECKS

1. [Primary bottleneck]
   - Evidence: [metrics]
   - Impact: [% of total time]

2. [Secondary bottleneck]
   - Evidence: [metrics]
   - Impact: [% of total time]

## OPTIMIZATION RECOMMENDATIONS

### High Impact (Recommended)

1. **[Optimization name]**
   - Problem: [description]
   - Solution: [specific change]
   - Expected improvement: [estimate]
   - Implementation:
     ```yaml
     [configuration change]
     ```
   - Risk: [LOW/MEDIUM/HIGH]

### Medium Impact

[Similar format]

### Low Impact

[Similar format]

## VALIDATION PLAN

1. [How to test the optimization]
2. [Metrics to monitor]
3. [Rollback procedure]

## ESTIMATED IMPROVEMENT

- Time: [current] → [estimated] ([X%] reduction)
- Cost: [current] → [estimated] ([X%] reduction)
- Confidence: [HIGH/MEDIUM/LOW]
```

## Example Analysis

### Scenario: Slow PostgreSQL Ingestion

**Analysis:**
- Current duration: 45 minutes
- Records: 10M rows
- No partitioning configured
- Sequential read from single partition

**Output:**
```markdown
## PERFORMANCE ANALYSIS

Pipeline: customer_orders
Analyzed runs: Last 5 runs
Current duration: 45 minutes
Data volume: 10M records (15GB)

## OBSERVED BOTTLENECKS

1. **Single-partition JDBC read** (PRIMARY)
   - Evidence: All data read through single Spark task
   - Evidence: 1 partition in source DataFrame
   - Impact: ~80% of execution time
   - Causes sequential read from PostgreSQL

2. **No predicate pushdown**
   - Evidence: Full table scan every time
   - Impact: ~15% of execution time

## OPTIMIZATION RECOMMENDATIONS

### High Impact (Recommended)

1. **Enable JDBC partitioned reads**
   - Problem: Reading 10M rows through single connection
   - Solution: Configure partition column and parallelism
   - Expected improvement: 70-80% reduction in read time
   - Implementation:
     ```yaml
     source:
       type: postgres
       table: orders
       partition_column: customer_id
       num_partitions: 8
       lower_bound: 1
       upper_bound: 1000000
     ```
   - Risk: LOW (read-only operation)

2. **Increase fetch size**
   - Problem: Default fetch size of 10,000 is too small
   - Solution: Increase to 50,000-100,000
   - Expected improvement: 10-15% reduction
   - Implementation:
     ```yaml
     source:
       fetch_size: 50000
     ```
   - Risk: LOW (higher memory per executor)

### Medium Impact

3. **Add partition pruning on target**
   - Problem: Not partitioning output by date
   - Solution: Partition Delta table by date column
   - Expected improvement: Faster subsequent queries
   - Implementation:
     ```yaml
     target:
       partition_by: [order_date]
     ```
   - Risk: LOW

## VALIDATION PLAN

1. Test on subset (1M records) first
2. Monitor task distribution in Spark UI
3. Verify all records loaded correctly
4. Compare execution time
5. Check executor memory usage
6. Rollback: Remove partitioning config if issues

## ESTIMATED IMPROVEMENT

- Time: 45 min → 8-10 min (78-82% reduction)
- Cost: $4.50/run → $0.90/run (80% reduction)
- Confidence: HIGH (well-understood optimization)
```

## Safety Considerations

- Never automatically modify production pipelines
- Always provide rollback procedures
- Estimate risks clearly
- Test optimizations on non-production first
- Monitor after changes
- Some optimizations may increase cost (trade-offs)

## Permissions

```yaml
permissions:
  metadata_read: true
  source_data_read: false
  target_data_read: false
  target_data_write: false
  pipeline_execution: false  # Only recommend, don't execute
  infrastructure_modify: false
```

## Best Practices

- Focus on high-impact changes first
- Provide specific configuration changes
- Estimate improvements realistically
- Explain trade-offs
- Include validation steps
- Give confidence levels
- Consider cost vs. speed trade-offs
- Think about maintainability
