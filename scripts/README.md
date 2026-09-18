# KDF Deployment Scripts

Automation scripts for deploying KDF pipelines to production environments.

## Scripts

### `databricks_setup.sh`

Initial setup script for KDF in a Databricks workspace.

**What it does:**
- Creates DBFS directory structure (`/kdf/configs`, `/kdf/wheels`, `/kdf/metadata`)
- Builds and uploads KDF wheel to DBFS
- Uploads runner notebook to workspace
- Validates Databricks CLI configuration

**Usage:**
```bash
# Make executable
chmod +x databricks_setup.sh

# Run setup
./databricks_setup.sh
```

**Prerequisites:**
- Databricks CLI installed (`pip install databricks-cli`)
- Databricks CLI configured (`databricks configure --token`)
- KDF installed (`pip install kdf`)

**Run this once per Databricks workspace.**

---

### `deploy_to_databricks.py`

Automated deployment script for CI/CD pipelines.

**What it does:**
- Validates KDF pipeline configuration
- Uploads config to DBFS
- Creates/updates Databricks workflow
- Optionally triggers workflow run
- Supports multiple environments (dev/staging/production)

**Usage:**

```bash
# Deploy to production with schedule
python deploy_to_databricks.py \
  --config medallion.yaml \
  --env production \
  --schedule "0 0 2 * * ?" \
  --emails team@company.com

# Dry run (generate workflow JSON without deploying)
python deploy_to_databricks.py \
  --config pipeline.yaml \
  --env staging \
  --dry-run

# Deploy and trigger immediately
python deploy_to_databricks.py \
  --config pipeline.yaml \
  --env dev \
  --trigger \
  --wait
```

**Options:**
- `--config`: Path to KDF pipeline config YAML (required)
- `--env`: Environment (dev/staging/production, default: production)
- `--workflow-name`: Custom workflow name
- `--schedule`: Cron schedule (e.g., "0 0 2 * * ?")
- `--emails`: Comma-separated notification emails
- `--dry-run`: Generate workflow JSON without deploying
- `--trigger`: Trigger workflow run after creation
- `--wait`: Wait for run to complete (requires --trigger)

**Exit Codes:**
- `0`: Success
- `1`: Failure (config invalid, deployment failed, etc.)

---

## CI/CD Integration

### GitHub Actions

```yaml
name: Deploy KDF Pipeline

on:
  push:
    branches: [main]
    paths:
      - 'pipelines/**/*.yaml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install kdf databricks-cli

      - name: Configure Databricks CLI
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
        run: |
          echo "$DATABRICKS_HOST" > ~/.databrickscfg
          echo "$DATABRICKS_TOKEN" >> ~/.databrickscfg

      - name: Deploy pipeline
        run: |
          python scripts/deploy_to_databricks.py \
            --config pipelines/medallion.yaml \
            --env production \
            --schedule "0 0 2 * * ?" \
            --emails ${{ secrets.NOTIFICATION_EMAIL }}
```

---

### GitLab CI

```yaml
deploy:
  stage: deploy
  image: python:3.9
  script:
    - pip install kdf databricks-cli
    - |
      cat > ~/.databrickscfg <<EOF
      [DEFAULT]
      host = $DATABRICKS_HOST
      token = $DATABRICKS_TOKEN
      EOF
    - python scripts/deploy_to_databricks.py
        --config pipelines/medallion.yaml
        --env production
        --schedule "0 0 2 * * ?"
        --emails $NOTIFICATION_EMAIL
  only:
    - main
  when: manual
```

---

### Jenkins

```groovy
pipeline {
    agent any

    environment {
        DATABRICKS_HOST = credentials('databricks-host')
        DATABRICKS_TOKEN = credentials('databricks-token')
    }

    stages {
        stage('Setup') {
            steps {
                sh 'pip install kdf databricks-cli'
                sh '''
                    cat > ~/.databrickscfg <<EOF
                    [DEFAULT]
                    host = ${DATABRICKS_HOST}
                    token = ${DATABRICKS_TOKEN}
                    EOF
                '''
            }
        }

        stage('Deploy') {
            steps {
                sh '''
                    python scripts/deploy_to_databricks.py \
                        --config pipelines/medallion.yaml \
                        --env production \
                        --schedule "0 0 2 * * ?" \
                        --emails team@company.com
                '''
            }
        }
    }
}
```

---

## Environment Management

### Separate Configs by Environment

```
pipelines/
├── dev/
│   └── medallion.yaml
├── staging/
│   └── medallion.yaml
└── production/
    └── medallion.yaml
```

### Deploy by Environment

```bash
# Deploy to dev
python deploy_to_databricks.py \
  --config pipelines/dev/medallion.yaml \
  --env dev

# Deploy to staging
python deploy_to_databricks.py \
  --config pipelines/staging/medallion.yaml \
  --env staging

# Deploy to production
python deploy_to_databricks.py \
  --config pipelines/production/medallion.yaml \
  --env production \
  --schedule "0 0 2 * * ?" \
  --emails oncall@company.com
```

---

## Secrets Management

### Using Environment Variables

```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="your-access-token"
export NOTIFICATION_EMAIL="team@company.com"

python deploy_to_databricks.py \
  --config pipeline.yaml \
  --env production \
  --emails $NOTIFICATION_EMAIL
```

### Using .env File

```bash
# .env
DATABRICKS_HOST=https://your-workspace.cloud.databricks.com
DATABRICKS_TOKEN=your-access-token
NOTIFICATION_EMAIL=team@company.com
```

```bash
# Load and deploy
source .env
python deploy_to_databricks.py \
  --config pipeline.yaml \
  --env production \
  --emails $NOTIFICATION_EMAIL
```

**⚠️ Never commit .env files to version control!**

---

## Rollback

If a deployment fails or causes issues:

1. **Pause the workflow:**
   ```bash
   databricks jobs update --job-id <ID> --pause
   ```

2. **Deploy previous version:**
   ```bash
   git checkout <previous-commit>
   python deploy_to_databricks.py --config pipeline.yaml --env production
   ```

3. **Or update workflow with previous config:**
   ```bash
   databricks jobs update --job-id <ID> --json-file previous_workflow.json
   ```

---

## Monitoring Deployments

### Check Workflow Status

```bash
# List all workflows
databricks jobs list

# Get workflow details
databricks jobs get --job-id <ID>

# Get run history
databricks runs list --job-id <ID> --limit 10
```

### Query Deployment Metadata

```sql
-- Recent deployments
SELECT
  pipeline_name,
  run_id,
  status,
  start_time,
  records_written
FROM delta.`/kdf/metadata/pipeline_runs`
WHERE DATE(start_time) = CURRENT_DATE()
ORDER BY start_time DESC;

-- Deployment success rate
SELECT
  pipeline_name,
  COUNT(*) as total_runs,
  SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful,
  ROUND(SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate
FROM delta.`/kdf/metadata/pipeline_runs`
WHERE start_time >= DATE_SUB(CURRENT_DATE(), 7)
GROUP BY pipeline_name;
```

---

## Best Practices

1. **Test in Dev First**
   ```bash
   python deploy_to_databricks.py --config pipeline.yaml --env dev --trigger --wait
   ```

2. **Use Dry Run for Validation**
   ```bash
   python deploy_to_databricks.py --config pipeline.yaml --env production --dry-run
   ```

3. **Version Control Workflows**
   ```bash
   # Save workflow JSON
   python deploy_to_databricks.py --config pipeline.yaml --dry-run > workflow_v1.json
   git add workflow_v1.json
   git commit -m "Add workflow v1"
   ```

4. **Monitor After Deployment**
   - Check first run manually
   - Verify data quality
   - Monitor for 24 hours

5. **Set Up Alerts**
   - Configure email notifications
   - Set up Slack/PagerDuty integrations
   - Monitor metadata for anomalies

---

## Troubleshooting

### Script Fails with "Databricks CLI not configured"

**Solution:**
```bash
databricks configure --token
# Enter your workspace URL and token
```

---

### Deployment Succeeds but Workflow Fails

**Solution:**
1. Check Databricks workflow logs
2. Verify config is uploaded: `databricks fs ls dbfs:/kdf/configs/production/`
3. Verify notebook exists: `databricks workspace ls /Workspace/kdf/notebooks/`
4. Check KDF wheel: `databricks fs ls dbfs:/kdf/wheels/`

---

### "Permission Denied" Error

**Solution:**
- Verify your Databricks token has job creation permissions
- Check workspace access level
- Contact workspace admin

---

## Support

For issues or questions:
- Check logs in Databricks UI
- Query metadata: `SELECT * FROM delta.'/kdf/metadata/pipeline_runs'`
- File an issue: [KDF GitHub Issues](https://github.com/krianno/kdf/issues)

---

## Quick Reference

```bash
# Initial setup (once per workspace)
./databricks_setup.sh

# Deploy to dev
python deploy_to_databricks.py --config pipeline.yaml --env dev --trigger

# Deploy to staging
python deploy_to_databricks.py --config pipeline.yaml --env staging

# Deploy to production
python deploy_to_databricks.py \
  --config pipeline.yaml \
  --env production \
  --schedule "0 0 2 * * ?" \
  --emails oncall@company.com
```
