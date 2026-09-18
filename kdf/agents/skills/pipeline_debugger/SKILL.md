# Pipeline Debugger Agent Skill

## Purpose

Investigate failed or degraded pipeline runs and produce structured root-cause analysis.

## When to Use

Use this skill when:
- A pipeline has failed
- Pipeline performance has degraded
- Data quality issues are detected
- Investigating unexpected behavior
- Analyzing error patterns

## Required Context

Before debugging, obtain:
- Pipeline name
- Run ID (if investigating specific failure)
- Error message or symptoms
- Time range of issue

## Available Tools

- `inspect_pipeline_run`: Get detailed run information
- `inspect_pipeline_history`: View recent runs
- `query_metadata`: Query metadata tables
- `inspect_schema`: Check current schema
- `compare_schema`: Compare schemas between runs

## Investigation Process

1. **Identify the Problem**
   - Get pipeline run details
   - Review error messages
   - Check execution status

2. **Gather Evidence**
   - Review recent pipeline history
   - Check for pattern of failures
   - Inspect metadata and metrics
   - Compare with successful runs

3. **Analyze Root Cause**
   - Schema changes
   - Data quality issues
   - Source availability
   - Configuration errors
   - Resource constraints

4. **Assess Impact**
   - Records affected
   - Data completeness
   - Downstream dependencies

5. **Recommend Actions**
   - Immediate fixes
   - Configuration changes
   - Schema updates
   - Monitoring improvements

## Output Format

Provide structured analysis:

```markdown
## ROOT CAUSE

[Clear, concise explanation of what caused the failure]

## EVIDENCE

- [Specific evidence from metadata]
- [Error messages or metrics]
- [Comparisons with successful runs]

## IMPACT

- Records affected: [number]
- Time range: [start] to [end]
- Data completeness: [percentage]
- Downstream systems: [list if known]

## RECOMMENDED ACTION

[Specific, actionable steps to resolve]

## CONFIDENCE

[HIGH | MEDIUM | LOW]
[Brief justification]
```

## Example Investigation

### Scenario: Pipeline Failed with "Column not found" Error

**Investigation:**
1. Check run details → Error: "Column 'order_total' not found"
2. Inspect schema history → Schema changed 2 hours ago
3. Compare schemas → Column renamed from 'order_total' to 'total_amount'
4. Review source system → Change deployed in source database

**Output:**
```markdown
## ROOT CAUSE

Breaking schema change in source system. Column 'order_total' was renamed to 'total_amount' in the source database, but the KDF pipeline configuration was not updated.

## EVIDENCE

- Pipeline run ID: orders_20260918_143052_a8f3
- Error: "Column 'order_total' not found in DataFrame"
- Schema history shows change at 2026-09-18 12:15:00 UTC
- Source system deployment logs confirm schema migration
- Last successful run used old schema

## IMPACT

- Records affected: 12,847 (all records since 14:30 UTC)
- Time range: 14:30 to current
- Data completeness: 0% for period
- Downstream systems: Revenue dashboard, Analytics warehouse (likely stale)

## RECOMMENDED ACTION

1. Update pipeline configuration to use new column name 'total_amount'
2. Add schema_evolution skill with mode: "warning" to detect future changes
3. Backfill failed period after configuration update
4. Coordinate with source team on schema change notifications

## CONFIDENCE

HIGH - Clear evidence of schema change matching error message.
```

## Safety Considerations

- This skill is READ-ONLY
- Never modify pipeline configurations automatically
- Never modify production data
- Never restart pipelines without user approval
- Always present analysis before recommending actions

## Permissions

```yaml
permissions:
  metadata_read: true
  source_data_read: true  # For investigation
  target_data_read: true  # For reconciliation
  target_data_write: false
  pipeline_execution: false
  infrastructure_modify: false
```

## Best Practices

- Start with the error message
- Look for patterns across multiple runs
- Compare failed runs with successful runs
- Check metadata for anomalies
- Consider timing of failures
- Don't fabricate evidence
- Distinguish facts from inferences
- Provide confidence levels
- Give specific, actionable recommendations
