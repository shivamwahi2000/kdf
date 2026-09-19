# KDF Discovery Questionnaire

**Client Name**: ___________________________
**Date**: ___________________________
**Completed By**: ___________________________
**Title**: ___________________________

**Instructions**: Please complete this questionnaire before our kickoff meeting. This information helps us understand your data landscape and design the best solution for your needs.

---

## 1. Organization & Project Overview

### 1.1 Company Information
- **Company Name**: ___________________________
- **Industry**: ___________________________
- **Company Size**:
  - [ ] <100 employees
  - [ ] 100-500 employees
  - [ ] 500-2,000 employees
  - [ ] 2,000-10,000 employees
  - [ ] >10,000 employees

### 1.2 Project Overview
**What is the primary business goal for this data engineering initiative?**
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

**What problem are you trying to solve?**
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

**What does success look like for this project?**
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

---

## 2. Current Data Landscape

### 2.1 Data Sources

**How many source systems do you need to integrate?**
- [ ] 1-5
- [ ] 6-15
- [ ] 16-30
- [ ] 30+

**Please list your top 5-10 data sources:**

| Source System | Type | Volume/Day | Refresh Frequency | Priority |
|---------------|------|-----------|-------------------|----------|
| (e.g., CRM) | (e.g., PostgreSQL) | (e.g., 100K records) | (e.g., Hourly) | (e.g., High) |
| 1. _____________ | _____________ | _____________ | _____________ | _____________ |
| 2. _____________ | _____________ | _____________ | _____________ | _____________ |
| 3. _____________ | _____________ | _____________ | _____________ | _____________ |
| 4. _____________ | _____________ | _____________ | _____________ | _____________ |
| 5. _____________ | _____________ | _____________ | _____________ | _____________ |
| 6. _____________ | _____________ | _____________ | _____________ | _____________ |
| 7. _____________ | _____________ | _____________ | _____________ | _____________ |
| 8. _____________ | _____________ | _____________ | _____________ | _____________ |
| 9. _____________ | _____________ | _____________ | _____________ | _____________ |
| 10. _____________ | _____________ | _____________ | _____________ | _____________ |

### 2.2 Source System Details

**For your top 3 priority sources, please provide:**

**Source #1**: ___________________________
- **Connection details**:
  - Host/URL: ___________________________
  - Port: ___________________________
  - Database/Schema: ___________________________
- **Access method**:
  - [ ] Direct database connection
  - [ ] API
  - [ ] File export (CSV/JSON/Parquet)
  - [ ] Other: ___________________________
- **Incremental loading**:
  - [ ] Yes, using column: ___________________________
  - [ ] No, full load required
- **Change Data Capture (CDC) available?**
  - [ ] Yes
  - [ ] No
- **Data volume**:
  - Total records: ___________________________
  - Growth rate: ___________ per month
- **Data freshness requirement (SLA)**:
  - [ ] Real-time (<5 min)
  - [ ] Near real-time (5-30 min)
  - [ ] Hourly
  - [ ] Daily
  - [ ] Weekly

*Repeat for Source #2 and #3*

---

## 3. Current Data Platform

### 3.1 Infrastructure

**Do you currently use Databricks?**
- [ ] Yes, in production
- [ ] Yes, in evaluation/POC
- [ ] No, but planning to adopt
- [ ] No, and not planning to adopt

**If yes, please provide:**
- Workspace URL: ___________________________
- Cloud provider: [ ] AWS  [ ] Azure  [ ] GCP
- Databricks tier: [ ] Standard  [ ] Premium  [ ] Enterprise
- Average cluster size: ___________________________
- Monthly Databricks spend: $___________________________

**What cloud provider do you use for data storage?**
- [ ] AWS (S3)
- [ ] Azure (ADLS Gen2)
- [ ] GCP (Cloud Storage)
- [ ] On-premises
- [ ] Hybrid

**Data lake/warehouse location**:
- S3 Bucket / ADLS Container / GCS Bucket: ___________________________
- Region: ___________________________
- Current data volume: ___________ TB

### 3.2 Current Data Stack

**What tools do you currently use for:**

**Orchestration**:
- [ ] Apache Airflow
- [ ] Databricks Workflows
- [ ] Azure Data Factory
- [ ] AWS Step Functions
- [ ] Luigi
- [ ] Prefect
- [ ] Custom scripts
- [ ] Other: ___________________________

**Data Transformation**:
- [ ] PySpark
- [ ] dbt
- [ ] SQL (direct)
- [ ] Pandas
- [ ] Custom Python scripts
- [ ] Scala
- [ ] Other: ___________________________

**Data Quality**:
- [ ] Great Expectations
- [ ] deequ
- [ ] Custom checks
- [ ] None currently
- [ ] Other: ___________________________

**Monitoring**:
- [ ] Databricks monitoring
- [ ] Datadog
- [ ] Splunk
- [ ] CloudWatch / Azure Monitor / Stackdriver
- [ ] Custom dashboards
- [ ] None currently
- [ ] Other: ___________________________

### 3.3 Current Pipeline Inventory

**How many data pipelines do you currently have in production?**
- [ ] 0 (starting fresh)
- [ ] 1-10
- [ ] 11-25
- [ ] 26-50
- [ ] 50-100
- [ ] 100+

**How are these pipelines currently built?**
- [ ] Custom Python/PySpark scripts
- [ ] dbt models
- [ ] SQL stored procedures
- [ ] Proprietary ETL tools
- [ ] Other: ___________________________

**Average time to build a new pipeline**:
- [ ] <1 day
- [ ] 1-3 days
- [ ] 1-2 weeks
- [ ] 2-4 weeks
- [ ] >1 month

---

## 4. Target Architecture & Requirements

### 4.1 Desired Architecture

**What architecture pattern are you targeting?**
- [ ] Medallion (Bronze → Silver → Gold)
- [ ] Data Lake
- [ ] Data Warehouse
- [ ] Lakehouse
- [ ] Not sure / want recommendations

**What execution modes do you need?**
- [ ] Batch processing
- [ ] Streaming (real-time)
- [ ] Micro-batch
- [ ] Mix of all above

**Data partitioning strategy**:
- [ ] By date (daily, monthly)
- [ ] By region/geography
- [ ] By customer/tenant
- [ ] No partitioning
- [ ] Other: ___________________________

### 4.2 Data Quality Requirements

**What data quality checks are required?**
- [ ] Not null validations
- [ ] Uniqueness checks
- [ ] Referential integrity
- [ ] Data freshness monitoring
- [ ] Custom business rules
- [ ] Schema validation
- [ ] Other: ___________________________

**When a quality check fails, what should happen?**
- [ ] Fail the pipeline immediately
- [ ] Log the error but continue
- [ ] Send alert but continue
- [ ] Quarantine bad records for review
- [ ] Other: ___________________________

### 4.3 Compliance & Security

**Do you have compliance requirements?**
- [ ] GDPR
- [ ] HIPAA
- [ ] SOC 2
- [ ] PCI-DSS
- [ ] CCPA
- [ ] None
- [ ] Other: ___________________________

**Data encryption requirements**:
- [ ] At rest (storage)
- [ ] In transit (network)
- [ ] Both
- [ ] Not required

**Data retention policies**:
- Bronze layer: ___________ days/months/years
- Silver layer: ___________ days/months/years
- Gold layer: ___________ days/months/years

**PII/sensitive data handling**:
- [ ] Masking required
- [ ] Encryption required
- [ ] Access controls required
- [ ] No special handling
- [ ] Other: ___________________________

---

## 5. Team & Resources

### 5.1 Data Engineering Team

**Current team size**:
- Data Engineers: ___________
- Analytics Engineers: ___________
- Data Analysts: ___________
- Data Scientists: ___________

**Primary programming languages**:
- [ ] Python
- [ ] Scala
- [ ] SQL
- [ ] R
- [ ] Java
- [ ] Other: ___________________________

**Experience with Spark/Databricks**:
- [ ] Expert (>3 years)
- [ ] Intermediate (1-3 years)
- [ ] Beginner (<1 year)
- [ ] No experience

**How much time can your team dedicate to this project?**
- [ ] Dedicated team (100%)
- [ ] 50-75% time
- [ ] 25-50% time
- [ ] <25% time

### 5.2 Stakeholders

**Who are the key stakeholders?**

| Role | Name | Email | Decision Authority |
|------|------|-------|---------------------|
| Executive Sponsor | _____________ | _____________ | [ ] Yes [ ] No |
| Technical Lead | _____________ | _____________ | [ ] Yes [ ] No |
| Data Lead | _____________ | _____________ | [ ] Yes [ ] No |
| Business Owner | _____________ | _____________ | [ ] Yes [ ] No |

---

## 6. Current Pain Points

**What are your biggest challenges with current data pipelines?** (Check all that apply)

- [ ] Too slow to develop new pipelines
- [ ] Pipelines break frequently
- [ ] Difficult to maintain
- [ ] No data quality monitoring
- [ ] High cloud costs
- [ ] Lack of documentation
- [ ] No testing framework
- [ ] Difficulty onboarding new engineers
- [ ] No metadata/lineage tracking
- [ ] Scalability issues
- [ ] Other: ___________________________

**Please describe your #1 pain point in detail**:
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

**What have you tried to solve it?**
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

---

## 7. Project Scope & Timeline

### 7.1 Initial Scope

**For the initial implementation, how many pipelines do you want to build?**
- [ ] 1-5 (POC/pilot)
- [ ] 6-15 (focused use case)
- [ ] 16-30 (department-wide)
- [ ] 30-50 (company-wide)
- [ ] 50+ (enterprise-scale)

**Top 3 priority pipelines for initial implementation**:

1. **Pipeline Name**: ___________________________
   - **Source**: ___________________________
   - **Target**: ___________________________
   - **Business Value**: ___________________________
   - **Current State**: [ ] Doesn't exist  [ ] Exists, needs migration

2. **Pipeline Name**: ___________________________
   - **Source**: ___________________________
   - **Target**: ___________________________
   - **Business Value**: ___________________________
   - **Current State**: [ ] Doesn't exist  [ ] Exists, needs migration

3. **Pipeline Name**: ___________________________
   - **Source**: ___________________________
   - **Target**: ___________________________
   - **Business Value**: ___________________________
   - **Current State**: [ ] Doesn't exist  [ ] Exists, needs migration

### 7.2 Timeline

**What is your target go-live date?**
- [ ] Within 1 month
- [ ] 1-3 months
- [ ] 3-6 months
- [ ] 6-12 months
- [ ] Flexible

**Any hard deadlines driven by business needs?**
_______________________________________________________________
_______________________________________________________________

### 7.3 Budget

**What is your approximate budget for this project?**
- [ ] <$50K
- [ ] $50K-$100K
- [ ] $100K-$250K
- [ ] $250K-$500K
- [ ] $500K-$1M
- [ ] >$1M
- [ ] Not yet determined

**Budget includes**:
- [ ] Software licenses
- [ ] Implementation services
- [ ] Training
- [ ] Ongoing support
- [ ] Infrastructure costs (Databricks, cloud)

---

## 8. Success Metrics

**How will you measure the success of this project?**

**Quantitative Metrics**:
- [ ] Reduction in pipeline development time (target: ___________%)
- [ ] Reduction in data processing costs (target: ___________%)
- [ ] Improvement in data freshness (target: ___________)
- [ ] Reduction in pipeline failures (target: ___________%)
- [ ] ROI (target: ___________%)
- [ ] Other: ___________________________

**Qualitative Metrics**:
- [ ] Improved data quality
- [ ] Better documentation
- [ ] Easier onboarding
- [ ] Increased data engineer productivity
- [ ] Faster time to insights
- [ ] Other: ___________________________

**What ROI are you expecting in Year 1?**
_______________________________________________________________

---

## 9. Additional Information

**Are there any other systems or considerations we should be aware of?**
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

**Do you have any specific concerns about adopting KDF?**
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

**What questions do you have for us?**
_______________________________________________________________
_______________________________________________________________
_______________________________________________________________

---

## 10. Next Steps

**What is your preferred next step?**
- [ ] Technical deep dive session
- [ ] POV (Proof of Value) with pilot pipelines
- [ ] Full implementation proposal
- [ ] Pricing discussion
- [ ] Other: ___________________________

**Best time for follow-up meeting**:
- Date: ___________________________
- Time: ___________________________
- Duration: ___________ hours
- Attendees: ___________________________

---

**Thank you for completing this questionnaire!**

We'll review your responses and prepare for our kickoff meeting. If you have any questions while completing this form, please contact:

**Krianno Contact**:
- Name: ___________________________
- Email: ___________________________
- Phone: ___________________________

**Completed Questionnaire**:
- [ ] Please return this form to: ___________________________
- [ ] By date: ___________________________
