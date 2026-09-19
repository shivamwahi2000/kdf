"""Project initialization CLI commands."""
import os
import shutil
from pathlib import Path
from typing import Optional
import click
import yaml


TEMPLATE_DIR = Path(__file__).parent.parent.parent / "templates" / "project"


@click.group(name="init")
def init_group():
    """Initialize a new KDF project."""
    pass


@init_group.command(name="project")
@click.argument("project_name")
@click.option("--path", "-p", default=".", help="Directory to create project in")
@click.option("--databricks/--no-databricks", default=True, help="Include Databricks integration")
@click.option("--cicd/--no-cicd", default=True, help="Include CI/CD workflows")
@click.option("--example-pipelines/--no-example-pipelines", default=True, help="Include example pipelines")
def init_project(
    project_name: str,
    path: str,
    databricks: bool,
    cicd: bool,
    example_pipelines: bool
):
    """Initialize a new KDF data engineering project.

    Creates a complete project structure with:
    - Pipeline configurations
    - Databricks integration (optional)
    - CI/CD workflows (optional)
    - Example pipelines (optional)

    Example:
        kdf init project my-data-project
        kdf init project my-data-project --path /projects --no-cicd
    """
    project_path = Path(path) / project_name

    if project_path.exists():
        click.echo(f"❌ Error: Directory {project_path} already exists!")
        return

    click.echo(f"🚀 Initializing KDF project: {project_name}")
    click.echo(f"📁 Location: {project_path}")
    click.echo()

    # Create project structure
    _create_project_structure(project_path, project_name)

    # Create configuration files
    _create_configs(project_path, project_name, example_pipelines)

    # Create Databricks integration
    if databricks:
        _create_databricks_integration(project_path, project_name)

    # Create CI/CD workflows
    if cicd:
        _create_cicd_workflows(project_path, project_name)

    # Create example pipelines
    if example_pipelines:
        _create_example_pipelines(project_path)

    # Create documentation
    _create_documentation(project_path, project_name)

    # Create requirements.txt
    _create_requirements(project_path)

    # Create .gitignore
    _create_gitignore(project_path)

    click.echo()
    click.echo("✅ Project initialized successfully!")
    click.echo()
    click.echo("📚 Next steps:")
    click.echo(f"   cd {project_name}")
    click.echo("   pip install -r requirements.txt")
    click.echo()
    click.echo("📖 Quick start:")
    click.echo("   1. Review configs/pipelines/*.yaml")
    click.echo("   2. Update with your data sources")
    click.echo("   3. Run: kdf run configs/pipelines/bronze_orders.yaml")
    click.echo()
    click.echo("📘 Documentation:")
    click.echo(f"   {project_path / 'README.md'}")
    click.echo()


def _create_project_structure(project_path: Path, project_name: str):
    """Create the base project directory structure."""
    directories = [
        "configs/pipelines",
        "configs/databricks",
        "notebooks",
        "scripts",
        "tests",
        "docs",
        ".github/workflows" if (TEMPLATE_DIR.parent.parent / ".github").exists() else None,
    ]

    for directory in directories:
        if directory:
            (project_path / directory).mkdir(parents=True, exist_ok=True)

    click.echo("✅ Created project structure")


def _create_configs(project_path: Path, project_name: str, include_examples: bool):
    """Create configuration files."""
    # Create empty __init__.py for Python package structure
    (project_path / "configs" / "__init__.py").write_text("")

    if not include_examples:
        return

    # Create example environment config
    env_config = {
        "environments": {
            "dev": {
                "data_path": "/tmp/data/dev",
                "checkpoint_path": "/tmp/checkpoints/dev",
                "metadata_path": "/tmp/metadata/dev"
            },
            "staging": {
                "data_path": "/data/staging",
                "checkpoint_path": "/checkpoints/staging",
                "metadata_path": "/metadata/staging"
            },
            "production": {
                "data_path": "/data/production",
                "checkpoint_path": "/checkpoints/production",
                "metadata_path": "/metadata/production"
            }
        }
    }

    with open(project_path / "configs" / "environments.yaml", "w") as f:
        yaml.dump(env_config, f, default_flow_style=False, sort_keys=False)

    click.echo("✅ Created configuration files")


def _create_databricks_integration(project_path: Path, project_name: str):
    """Create Databricks integration files."""
    # Create databricks.yml
    databricks_config = {
        "bundle": {
            "name": project_name.replace("-", "_")
        },
        "workspace": {
            "root_path": "/Workspace/.bundle/${bundle.name}/${bundle.target}"
        },
        "targets": {
            "dev": {
                "mode": "development",
                "workspace": {
                    "host": "${var.databricks_host_dev}"
                },
                "variables": {
                    "environment": "dev",
                    "config_path": f"/kdf/{project_name}/configs/dev"
                }
            },
            "production": {
                "mode": "production",
                "workspace": {
                    "host": "${var.databricks_host_prod}"
                },
                "variables": {
                    "environment": "production",
                    "config_path": f"/kdf/{project_name}/configs/production"
                },
                "run_as": {
                    "service_principal_name": "${var.service_principal_name}"
                }
            }
        },
        "include": [
            "configs/databricks/*.yml"
        ]
    }

    with open(project_path / "databricks.yml", "w") as f:
        yaml.dump(databricks_config, f, default_flow_style=False, sort_keys=False)

    # Create basic job configuration
    job_config = {
        "resources": {
            "jobs": {
                f"{project_name.replace('-', '_')}_pipeline": {
                    "name": f"{project_name} - Data Pipeline",
                    "tasks": [
                        {
                            "task_key": "run_pipeline",
                            "description": "Run data pipeline",
                            "python_wheel_task": {
                                "package_name": "kdf",
                                "entry_point": "main",
                                "parameters": [
                                    "run",
                                    "${var.config_path}/pipeline.yaml"
                                ]
                            },
                            "libraries": [
                                {"pypi": {"package": "kdf"}}
                            ],
                            "new_cluster": {
                                "spark_version": "13.3.x-scala2.12",
                                "node_type_id": "i3.xlarge",
                                "num_workers": 2,
                                "runtime_engine": "PHOTON"
                            }
                        }
                    ],
                    "email_notifications": {
                        "on_failure": ["${var.notification_email}"]
                    },
                    "tags": {
                        "project": project_name,
                        "framework": "kdf"
                    }
                }
            }
        }
    }

    with open(project_path / "configs" / "databricks" / "job.yml", "w") as f:
        yaml.dump(job_config, f, default_flow_style=False, sort_keys=False)

    click.echo("✅ Created Databricks integration")


def _create_cicd_workflows(project_path: Path, project_name: str):
    """Create CI/CD workflow files."""
    github_dir = project_path / ".github" / "workflows"
    github_dir.mkdir(parents=True, exist_ok=True)

    # Create dev workflow
    dev_workflow = """name: Deploy to Dev

on:
  push:
    branches: [develop]

jobs:
  deploy-dev:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install dependencies
        run: |
          pip install kdf

      - name: Validate configurations
        run: |
          kdf validate configs/pipelines/*.yaml

      - name: Deploy to Databricks Dev
        if: contains(github.repository, 'databricks')
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST_DEV }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN_DEV }}
        run: |
          databricks bundle deploy -t dev
"""

    (github_dir / "deploy-dev.yml").write_text(dev_workflow)

    click.echo("✅ Created CI/CD workflows")


def _create_example_pipelines(project_path: Path):
    """Create example pipeline configurations."""
    pipelines_dir = project_path / "configs" / "pipelines"

    # Bronze pipeline example
    bronze_pipeline = {
        "name": "bronze_orders",
        "description": "Ingest raw orders from PostgreSQL to Bronze layer",
        "execution_mode": "batch",
        "source": {
            "type": "postgres",
            "host": "${env.POSTGRES_HOST}",
            "port": 5432,
            "database": "production",
            "schema": "public",
            "table": "orders",
            "incremental": {
                "column": "updated_at",
                "start": "2024-01-01"
            }
        },
        "target": {
            "type": "delta",
            "path": "${env.data_path}/bronze/orders",
            "mode": "append",
            "partition_by": ["order_date"]
        },
        "metadata": {
            "enabled": True,
            "path": "${env.metadata_path}"
        }
    }

    with open(pipelines_dir / "bronze_orders.yaml", "w") as f:
        yaml.dump(bronze_pipeline, f, default_flow_style=False, sort_keys=False)

    # Silver pipeline example
    silver_pipeline = {
        "name": "silver_orders",
        "description": "Clean and validate orders in Silver layer",
        "execution_mode": "batch",
        "source": {
            "type": "delta",
            "path": "${env.data_path}/bronze/orders"
        },
        "skills": [
            {
                "deduplicate": {
                    "keys": ["order_id"],
                    "order_by": "updated_at"
                }
            }
        ],
        "quality": [
            {
                "not_null": {
                    "columns": ["order_id", "customer_id", "order_date"]
                }
            },
            {
                "unique": {
                    "columns": ["order_id"]
                }
            }
        ],
        "target": {
            "type": "delta",
            "path": "${env.data_path}/silver/orders",
            "mode": "overwrite",
            "partition_by": ["order_date"]
        },
        "metadata": {
            "enabled": True,
            "path": "${env.metadata_path}"
        }
    }

    with open(pipelines_dir / "silver_orders.yaml", "w") as f:
        yaml.dump(silver_pipeline, f, default_flow_style=False, sort_keys=False)

    # Gold pipeline example
    gold_pipeline = {
        "name": "gold_daily_revenue",
        "description": "Calculate daily revenue metrics",
        "execution_mode": "batch",
        "source": {
            "type": "delta",
            "path": "${env.data_path}/silver/orders"
        },
        "skills": [
            {
                "aggregate": {
                    "group_by": ["order_date", "product_category"],
                    "metrics": [
                        {"name": "total_revenue", "agg": "sum", "column": "amount"},
                        {"name": "order_count", "agg": "count"},
                        {"name": "avg_order_value", "agg": "avg", "column": "amount"},
                        {"name": "unique_customers", "agg": "countDistinct", "column": "customer_id"}
                    ]
                }
            }
        ],
        "target": {
            "type": "delta",
            "path": "${env.data_path}/gold/daily_revenue",
            "mode": "overwrite"
        },
        "metadata": {
            "enabled": True,
            "path": "${env.metadata_path}"
        }
    }

    with open(pipelines_dir / "gold_daily_revenue.yaml", "w") as f:
        yaml.dump(gold_pipeline, f, default_flow_style=False, sort_keys=False)

    # Medallion multi-pipeline config
    medallion_config = {
        "name": "medallion_orders",
        "description": "Complete Medallion architecture for orders",
        "pipelines": [
            {
                "name": "bronze_orders",
                "config_file": "configs/pipelines/bronze_orders.yaml"
            },
            {
                "name": "silver_orders",
                "config_file": "configs/pipelines/silver_orders.yaml",
                "depends_on": ["bronze_orders"]
            },
            {
                "name": "gold_daily_revenue",
                "config_file": "configs/pipelines/gold_daily_revenue.yaml",
                "depends_on": ["silver_orders"]
            }
        ],
        "metadata": {
            "enabled": True,
            "path": "${env.metadata_path}"
        }
    }

    with open(pipelines_dir / "medallion_orders.yaml", "w") as f:
        yaml.dump(medallion_config, f, default_flow_style=False, sort_keys=False)

    click.echo("✅ Created example pipelines (Bronze, Silver, Gold)")


def _create_documentation(project_path: Path, project_name: str):
    """Create project documentation."""
    readme_content = f"""# {project_name}

Data engineering project built with [KDF (Krianno Data Framework)](https://github.com/shivamwahi2000/kdf)

## Overview

This project implements a modern data pipeline using:
- ✅ **Medallion Architecture** (Bronze → Silver → Gold)
- ✅ **S3 Autoloader** for incremental ingestion
- ✅ **Delta Lake** for ACID transactions
- ✅ **Databricks** integration (optional)
- ✅ **CI/CD** workflows (optional)

## Project Structure

```
{project_name}/
├── configs/
│   ├── pipelines/              # Pipeline configurations
│   │   ├── bronze_orders.yaml
│   │   ├── silver_orders.yaml
│   │   ├── gold_daily_revenue.yaml
│   │   └── medallion_orders.yaml
│   ├── databricks/             # Databricks job configs
│   └── environments.yaml       # Environment settings
├── notebooks/                  # Databricks notebooks
├── scripts/                    # Utility scripts
├── tests/                      # Tests
├── docs/                       # Documentation
├── databricks.yml              # Databricks Asset Bundle config
└── requirements.txt
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Update `configs/environments.yaml` with your environment settings.

Set environment variables:
```bash
export POSTGRES_HOST=your-postgres-host
export POSTGRES_USER=your-user
export POSTGRES_PASSWORD=your-password
```

### 3. Run Pipelines

**Run single pipeline:**
```bash
kdf run configs/pipelines/bronze_orders.yaml
```

**Run medallion workflow:**
```bash
kdf run configs/pipelines/medallion_orders.yaml
```

**Run with specific environment:**
```bash
kdf run configs/pipelines/bronze_orders.yaml --env production
```

### 4. Deploy to Databricks (Optional)

```bash
# Validate bundle
databricks bundle validate -t dev

# Deploy to dev
databricks bundle deploy -t dev

# Run job
databricks bundle run -t dev {project_name.replace('-', '_')}_pipeline
```

## Pipelines

### Bronze Layer
- **Pipeline**: `bronze_orders.yaml`
- **Purpose**: Ingest raw data from PostgreSQL
- **Features**: Incremental loading, partitioning

### Silver Layer
- **Pipeline**: `silver_orders.yaml`
- **Purpose**: Clean and validate data
- **Features**: Deduplication, quality checks

### Gold Layer
- **Pipeline**: `gold_daily_revenue.yaml`
- **Purpose**: Calculate business metrics
- **Features**: Aggregations, analytics-ready data

## Configuration

### Pipeline Configuration

Each pipeline is defined in YAML:

```yaml
name: my_pipeline
execution_mode: batch  # or streaming, micro_batch

source:
  type: postgres
  host: ${{env.POSTGRES_HOST}}
  table: orders

target:
  type: delta
  path: /data/bronze/orders
  mode: append
```

### Environment Variables

Use environment variables for sensitive data:
- `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `DATABRICKS_HOST`, `DATABRICKS_TOKEN`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`

## Development

### Run Tests

```bash
pytest tests/
```

### Validate Configurations

```bash
kdf validate configs/pipelines/*.yaml
```

### Local Development

```bash
# Run with local environment
export ENVIRONMENT=dev
kdf run configs/pipelines/bronze_orders.yaml
```

## Deployment

### CI/CD

GitHub Actions workflows are configured for:
- **Dev**: Auto-deploy on push to `develop`
- **Production**: Manual approval for `main` branch

### Databricks

Deploy using Asset Bundles:

```bash
# Development
databricks bundle deploy -t dev

# Production
databricks bundle deploy -t production
```

## Monitoring

### Query Metadata

```sql
SELECT
  pipeline_name,
  status,
  records_read,
  records_written,
  execution_time_seconds,
  start_time,
  end_time
FROM delta.`/metadata/pipeline_runs`
WHERE pipeline_name = 'bronze_orders'
ORDER BY start_time DESC
LIMIT 10;
```

### View Pipeline Lineage

```sql
SELECT
  pipeline_name,
  source_type,
  source_path,
  target_type,
  target_path
FROM delta.`/metadata/pipelines`
WHERE pipeline_name LIKE '%orders%';
```

## Resources

- **KDF Documentation**: https://github.com/shivamwahi2000/kdf
- **Databricks Asset Bundles**: https://docs.databricks.com/dev-tools/bundles/
- **Delta Lake**: https://delta.io/

## License

MIT License

## Support

For issues and questions:
- KDF Issues: https://github.com/shivamwahi2000/kdf/issues
- Project Issues: Create issue in this repository
"""

    (project_path / "README.md").write_text(readme_content)

    click.echo("✅ Created documentation")


def _create_requirements(project_path: Path):
    """Create requirements.txt."""
    requirements = """# KDF Framework
kdf>=0.1.0

# Data Processing
pyspark>=3.3.0

# Database Connectors
psycopg2-binary>=2.9.0

# AWS
boto3>=1.26.0

# Configuration
pyyaml>=6.0
python-dotenv>=0.19.0

# Databricks (optional)
databricks-cli>=0.17.0

# Testing
pytest>=7.0.0
pytest-cov>=3.0.0
"""

    (project_path / "requirements.txt").write_text(requirements)

    click.echo("✅ Created requirements.txt")


def _create_gitignore(project_path: Path):
    """Create .gitignore."""
    gitignore_content = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
env/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# Jupyter
.ipynb_checkpoints

# Environment
.env
.env.local

# Databricks
.databricks/

# Data
data/
*.parquet
*.csv
*.json

# Logs
logs/
*.log

# Temporary
tmp/
temp/
.tmp/

# OS
.DS_Store
Thumbs.db
"""

    (project_path / ".gitignore").write_text(gitignore_content)

    click.echo("✅ Created .gitignore")
