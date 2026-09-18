# Data Quality Investigator Agent Skill

## Purpose

Investigate why data quality checks failed and identify root causes of data anomalies.

## When to Use

Use this skill when:
- Data quality check fails
- Anomalies detected in data
- Unexpected null rates
- Duplicate records found
- Freshness violations
- Investigating data patterns

## Required Context

- Pipeline name
- Quality check that failed
- Run ID
- Specific columns affected
- Historical baseline (if available)

## Available Tools

- `inspect_pipeline_run`: Get quality check results
- `inspect_pipeline_history`: Analyze trends
- `query_metadata`: Query quality metrics over time
- `inspect_schema`: Check schema
- SQL queries for data profiling

## Investigation Process

1. **Understand the Failure**
   - What check failed?
   - What column(s) affected?
   - What's the violation count?
   - When did it start?

2. **Establish Baseline**
   - What's normal for this check?
   - Historical trends
   - Previous failure patterns

3. **Analyze the Data**
   - Profile affected columns
   - Check source data
   - Look for patterns
   - Correlate with other changes

4. **Identify Root Cause**
   - Source system issue
   - Pipeline configuration
   - Schema change
   - Business logic change
   - Data generation issue

5. **Assess Severity**
   - How bad is it?
   - Is it getting worse?
   - Impact on downstream systems

## Output Format

```markdown
## QUALITY ISSUE

[Clear description of what failed]

## OBSERVED FACTS

- [Specific measurements]
- [Violation counts]
- [Time periods]
- [Affected columns]

## HISTORICAL CONTEXT

- [Normal baseline]
- [Trend analysis]
- [Previous occurrences]

## POTENTIAL ROOT CAUSES

1. [Most likely cause]
   - Evidence: [...]
   - Confidence: [HIGH/MEDIUM/LOW]

2. [Alternative explanation]
   - Evidence: [...]
   - Confidence: [HIGH/MEDIUM/LOW]

## SEVERITY

[CRITICAL | HIGH | MEDIUM | LOW]
[Justification]

## RECOMMENDATIONS

1. [Immediate action]
2. [Investigation steps]
3. [Long-term fixes]

## NOTES

[Any additional observations]
```

## Example Investigation

### Scenario: Null Rate Spike

**Input:** "Customer_id null rate increased from 0.2% to 17.4% in today's run"

**Investigation:**
1. Check run metadata → 21,842 nulls out of 125,421 records
2. Query historical data → Baseline: 0.1-0.3% over last 30 days
3. Profile the data → Nulls concentrated in records after 14:00 UTC
4. Check schema history → No schema changes
5. Analyze source patterns → New mobile app deployment at 13:45 UTC

**Output:**
```markdown
## QUALITY ISSUE

`not_null` check failed for `customer_id` column. Null rate increased from 0.2% to 17.4% (21,842 violations out of 125,421 records).

## OBSERVED FACTS

- Pipeline: orders_ingestion
- Run ID: orders_20260918_150030_b7c2
- Column: customer_id
- Violations: 21,842 (17.4%)
- Time range: 14:00-15:00 UTC
- Historical baseline: 0.1-0.3% (normal)

## HISTORICAL CONTEXT

- Last 30 days: null rate consistently 0.1-0.3%
- No similar spikes in history
- Previous high: 0.4% on 2026-09-10
- Today's spike is 58x normal rate

## POTENTIAL ROOT CAUSES

1. **Mobile app update introduced bug** (HIGH CONFIDENCE)
   - Evidence: New app version deployed at 13:45 UTC
   - Evidence: Nulls concentrated in records after 14:00 UTC
   - Evidence: Mobile order source_id matches affected records
   - Correlation: Timing matches exactly

2. **API authentication issue** (MEDIUM CONFIDENCE)
   - Evidence: Some orders processed without customer context
   - Evidence: Order data present but customer_id missing
   - May be related to mobile app issue

## SEVERITY

HIGH
- 17% of orders missing customer association
- Impacts customer analytics, personalization, and retention tracking
- Affects revenue attribution
- Issue is ongoing (still receiving bad data)

## RECOMMENDATIONS

1. **IMMEDIATE**: Alert mobile engineering team about customer_id null issue post-deployment
2. **IMMEDIATE**: Consider temporarily rejecting orders without customer_id (business decision)
3. **INVESTIGATION**: Review mobile app logs for authentication/session issues
4. **DATA**: Backfill customer_id using session_id or device_id correlation if possible
5. **MONITORING**: Add quality check alerting to catch issues within 15 minutes
6. **LONG-TERM**: Implement source-side validation to prevent nulls

## NOTES

- Issue appears limited to mobile orders
- Web and API orders unaffected
- May be able to recover customer_id from session data
- Need to coordinate with mobile and data engineering teams
```

## Safety Considerations

- Never modify data during investigation
- Distinguish observation from inference
- Provide evidence for all claims
- Don't fabricate data
- Admit uncertainty where appropriate
- Mark confidence levels clearly

## Permissions

```yaml
permissions:
  metadata_read: true
  source_data_read: true
  target_data_read: true
  target_data_write: false
  pipeline_execution: false
  infrastructure_modify: false
```

## Best Practices

- Start with the facts
- Check historical context
- Look for correlating events
- Profile the actual data
- Consider multiple hypotheses
- Provide confidence levels
- Recommend specific actions
- Escalate when needed
