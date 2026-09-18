"""KDF command-line interface."""

import click
import sys
from pathlib import Path
from tabulate import tabulate

# Bootstrap registries
import kdf.bootstrap

from kdf.core.config import PipelineConfig
from kdf.core.pipeline import Pipeline
from kdf.core.context import ExecutionContext
from kdf.core.registry import connector_registry, skill_registry
from kdf.metadata.runs import RunMetadataStore
from kdf.cli.medallion import run_medallion, validate_medallion
from kdf.cli.databricks import databricks


@click.group()
@click.version_option(version="0.1.0", prog_name="KDF")
def cli():
    """KDF — Krianno Data Framework

    Build the foundation for Agentic Data Engineering.
    """
    pass


@cli.command()
@click.option("--path", default=".", help="Project directory")
def init(path: str):
    """Initialize a new KDF project."""
    project_path = Path(path)
    project_path.mkdir(exist_ok=True)

    # Create example pipeline
    example_pipeline = """# Example KDF Pipeline Configuration

name: example_pipeline

source:
  type: postgres
  connection: my_postgres
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

target:
  type: delta
  path: /data/orders
  mode: append
"""

    pipeline_file = project_path / "pipeline.yaml"
    if not pipeline_file.exists():
        pipeline_file.write_text(example_pipeline)
        click.echo(f"✓ Created example pipeline: {pipeline_file}")

    # Create .env template
    env_template = """# KDF Environment Configuration

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=mydb
POSTGRES_USER=user
POSTGRES_PASSWORD=password

# AWS / S3
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# Metadata
KDF_METADATA_PATH=./kdf_metadata
"""

    env_file = project_path / ".env.template"
    if not env_file.exists():
        env_file.write_text(env_template)
        click.echo(f"✓ Created environment template: {env_file}")

    click.echo("\n✓ KDF project initialized!")
    click.echo("\nNext steps:")
    click.echo("  1. Copy .env.template to .env and configure your credentials")
    click.echo("  2. Edit pipeline.yaml to match your use case")
    click.echo("  3. Run: kdf validate pipeline.yaml")
    click.echo("  4. Run: kdf run pipeline.yaml")


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
def validate(config_file: str):
    """Validate a pipeline configuration."""
    try:
        config = PipelineConfig.from_yaml(config_file)
        pipeline = Pipeline(config)
        pipeline.validate()

        click.echo(f"✓ Configuration valid: {config_file}")
        click.echo(f"\nPipeline: {config.name}")
        click.echo(f"Source: {config.source.type}")
        click.echo(f"Target: {config.target.path}")

        if config.ingestion:
            click.echo(f"Ingestion: {config.ingestion.skill}")

        if config.skills:
            click.echo(f"Skills: {len(config.skills)}")

        if config.quality:
            click.echo(f"Quality checks: {len(config.quality)}")

    except Exception as e:
        click.echo(f"✗ Validation failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--spark-master", help="Spark master URL")
@click.option("--metadata-path", default="./kdf_metadata", help="Metadata storage path")
def run(config_file: str, spark_master: str, metadata_path: str):
    """Run a pipeline."""
    try:
        # Load configuration
        config = PipelineConfig.from_yaml(config_file)

        # Create pipeline
        pipeline = Pipeline(config)

        # Create execution context
        context = ExecutionContext(
            config=config,
            metadata_path=metadata_path,
        )

        click.echo(f"Starting pipeline: {config.name}")
        click.echo(f"Run ID: {context.run_id}")

        # Execute pipeline
        result = pipeline.run(context)

        # Save run metadata
        store = RunMetadataStore(context.spark, metadata_path)
        store.save_run(result.get_pipeline_run())

        # Display results
        click.echo(f"\n✓ Pipeline completed: {result.status.value}")
        click.echo(f"\nMetrics:")
        click.echo(f"  Records read: {result.metrics.get('records_read', 'N/A')}")
        click.echo(f"  Records written: {result.metrics.get('records_written', 'N/A')}")

        if result.errors:
            click.echo(f"\nErrors:")
            for error in result.errors:
                click.echo(f"  - {error}")

    except Exception as e:
        click.echo(f"✗ Pipeline failed: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--metadata-path", default="./kdf_metadata", help="Metadata storage path")
def status(metadata_path: str):
    """Show KDF status and recent runs."""
    from pyspark.sql import SparkSession

    try:
        spark = SparkSession.builder.appName("KDF Status").getOrCreate()
        store = RunMetadataStore(spark, metadata_path)

        # Try to read recent runs
        df = spark.read.format("delta").load(f"{metadata_path}/pipeline_runs")
        recent_runs = df.orderBy("start_time", ascending=False).limit(10).collect()

        if not recent_runs:
            click.echo("No pipeline runs found.")
            return

        # Format as table
        table_data = []
        for row in recent_runs:
            table_data.append([
                row["pipeline_name"],
                row["status"],
                row["start_time"].strftime("%Y-%m-%d %H:%M:%S"),
                row["records_read"] or "N/A",
                row["records_written"] or "N/A",
            ])

        headers = ["Pipeline", "Status", "Start Time", "Read", "Written"]
        click.echo(tabulate(table_data, headers=headers, tablefmt="simple"))

    except Exception as e:
        click.echo(f"Unable to read status: {e}", err=True)


@cli.command()
@click.argument("pipeline_name")
@click.option("--limit", default=10, help="Number of runs to show")
@click.option("--metadata-path", default="./kdf_metadata", help="Metadata storage path")
def history(pipeline_name: str, limit: int, metadata_path: str):
    """Show pipeline execution history."""
    from pyspark.sql import SparkSession

    try:
        spark = SparkSession.builder.appName("KDF History").getOrCreate()
        store = RunMetadataStore(spark, metadata_path)

        runs = store.get_pipeline_history(pipeline_name, limit)

        if not runs:
            click.echo(f"No runs found for pipeline: {pipeline_name}")
            return

        # Format as table
        table_data = []
        for run in runs:
            duration = "N/A"
            if run.end_time:
                delta = run.end_time - run.start_time
                duration = f"{delta.total_seconds():.1f}s"

            table_data.append([
                run.run_id,
                run.status.value,
                run.start_time.strftime("%Y-%m-%d %H:%M:%S"),
                duration,
                run.records_read or "N/A",
                run.records_written or "N/A",
            ])

        headers = ["Run ID", "Status", "Start Time", "Duration", "Read", "Written"]
        click.echo(f"\nHistory for pipeline: {pipeline_name}\n")
        click.echo(tabulate(table_data, headers=headers, tablefmt="simple"))

    except Exception as e:
        click.echo(f"Unable to read history: {e}", err=True)


@cli.group()
def skill():
    """Manage KDF skills."""
    pass


@skill.command("list")
def skill_list():
    """List registered skills."""
    skills = skill_registry.list()

    if not skills:
        click.echo("No skills registered.")
        return

    click.echo("Registered skills:\n")
    for skill_name in sorted(skills):
        click.echo(f"  - {skill_name}")


@cli.group()
def connector():
    """Manage KDF connectors."""
    pass


@connector.command("list")
def connector_list():
    """List registered connectors."""
    connectors = connector_registry.list()

    if not connectors:
        click.echo("No connectors registered.")
        return

    click.echo("Registered connectors:\n")
    for conn_name in sorted(connectors):
        click.echo(f"  - {conn_name}")


# Add medallion commands
cli.add_command(run_medallion, name="run-medallion")
cli.add_command(validate_medallion, name="validate-medallion")

# Add databricks commands
cli.add_command(databricks)


if __name__ == "__main__":
    cli()
