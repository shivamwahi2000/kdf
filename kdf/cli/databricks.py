"""
Databricks deployment commands for KDF.
"""

import click
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional

from kdf.core.config import PipelineConfig, MedallionPipelineConfig
from kdf.databricks.workflow_builder import (
    create_medallion_workflow_from_config,
    WorkflowBuilder,
    ClusterConfig,
)


@click.group()
def databricks():
    """Databricks Workflows deployment commands."""
    pass


@databricks.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option(
    "--dbfs-path",
    default="/kdf/configs",
    help="DBFS path to upload config to",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite if config already exists",
)
def upload_config(config_file: str, dbfs_path: str, overwrite: bool):
    """
    Upload KDF pipeline config to DBFS.

    Example:
        kdf databricks upload-config my_pipeline.yaml --dbfs-path /kdf/configs
    """
    config_path = Path(config_file)

    if not config_path.exists():
        click.echo(f"✗ Config file not found: {config_file}", err=True)
        sys.exit(1)

    # Construct DBFS destination path
    dbfs_destination = f"dbfs:{dbfs_path}/{config_path.name}"

    click.echo(f"Uploading config to Databricks...")
    click.echo(f"  Source: {config_file}")
    click.echo(f"  Destination: {dbfs_destination}")

    # Use databricks CLI to upload
    cmd = ["databricks", "fs", "cp", str(config_path), dbfs_destination]
    if overwrite:
        cmd.append("--overwrite")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        click.echo(f"✓ Config uploaded successfully")
        click.echo(f"  DBFS Path: {dbfs_destination}")

    except subprocess.CalledProcessError as e:
        click.echo(f"✗ Failed to upload config", err=True)
        click.echo(f"  Error: {e.stderr}", err=True)
        sys.exit(1)

    except FileNotFoundError:
        click.echo(
            "✗ Databricks CLI not found. Please install: pip install databricks-cli",
            err=True,
        )
        sys.exit(1)


@databricks.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option(
    "--workflow-name",
    help="Databricks workflow name (defaults to config name)",
)
@click.option(
    "--config-path",
    help="DBFS path where config will be uploaded (e.g., dbfs:/kdf/configs/my_pipeline.yaml)",
)
@click.option(
    "--schedule",
    help="Cron schedule (e.g., '0 0 2 * * ?' for daily at 2am)",
)
@click.option(
    "--notification-emails",
    help="Comma-separated email addresses for failure notifications",
)
@click.option(
    "--output",
    type=click.Path(),
    help="Save workflow JSON to file instead of creating in Databricks",
)
def create_workflow(
    config_file: str,
    workflow_name: Optional[str],
    config_path: Optional[str],
    schedule: Optional[str],
    notification_emails: Optional[str],
    output: Optional[str],
):
    """
    Create Databricks workflow from KDF config.

    For single pipeline configs, creates a simple workflow.
    For medallion configs, creates multi-task workflow with dependencies.

    Example:
        kdf databricks create-workflow medallion.yaml \\
            --config-path dbfs:/kdf/configs/medallion.yaml \\
            --schedule "0 0 2 * * ?" \\
            --notification-emails team@company.com
    """
    config_file_path = Path(config_file)

    if not config_file_path.exists():
        click.echo(f"✗ Config file not found: {config_file}", err=True)
        sys.exit(1)

    click.echo(f"Creating Databricks workflow from {config_file}...")

    # Determine config type
    try:
        config = MedallionPipelineConfig.from_yaml(config_file)
        config_type = "medallion"
        click.echo(f"  Config type: Medallion ({len(config.pipelines)} pipelines)")
    except Exception:
        try:
            config = PipelineConfig.from_yaml(config_file)
            config_type = "single"
            click.echo(f"  Config type: Single pipeline")
        except Exception as e:
            click.echo(f"✗ Failed to load config: {e}", err=True)
            sys.exit(1)

    # Determine DBFS config path
    if not config_path:
        config_path = f"dbfs:/kdf/configs/{config_file_path.name}"

    click.echo(f"  DBFS config path: {config_path}")

    # Parse notification emails
    emails = None
    if notification_emails:
        emails = [e.strip() for e in notification_emails.split(",")]
        click.echo(f"  Notifications: {', '.join(emails)}")

    # Create workflow JSON
    try:
        if config_type == "medallion":
            workflow_json = create_medallion_workflow_from_config(
                medallion_config=config,
                workflow_name=workflow_name,
                config_path=config_path,
                schedule_cron=schedule,
                notification_emails=emails,
            )
        else:
            # Single pipeline workflow
            builder = WorkflowBuilder(
                name=workflow_name or f"KDF {config.name}",
            )

            builder.add_cluster(
                "kdf_cluster",
                ClusterConfig(
                    num_workers=2,
                    spark_conf={
                        "spark.databricks.delta.preview.enabled": "true",
                        "spark.sql.adaptive.enabled": "true",
                    },
                    custom_tags={"framework": "kdf", "version": "0.1"},
                ),
            )

            builder.add_single_pipeline_task(
                task_key="run_pipeline",
                config_path=config_path,
                cluster_key="kdf_cluster",
                description=f"Run {config.name}",
            )

            if schedule:
                builder.set_schedule(schedule)

            if emails:
                builder.set_email_notifications(on_failure=emails)

            workflow_json = builder.build()

        click.echo(f"✓ Workflow JSON generated")

        # Save to file or create in Databricks
        if output:
            output_path = Path(output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w") as f:
                json.dump(workflow_json, f, indent=2)

            click.echo(f"✓ Workflow saved to {output}")

        else:
            # Create workflow via Databricks CLI
            click.echo(f"\nCreating workflow in Databricks...")

            # Write to temp file
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(workflow_json, f, indent=2)
                temp_file = f.name

            try:
                cmd = ["databricks", "jobs", "create", "--json-file", temp_file]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

                # Parse response to get job ID
                response = json.loads(result.stdout)
                job_id = response.get("job_id")

                click.echo(f"✓ Workflow created successfully")
                click.echo(f"  Job ID: {job_id}")
                click.echo(
                    f"  URL: https://<workspace>.databricks.com/#job/{job_id}"
                )

            except subprocess.CalledProcessError as e:
                click.echo(f"✗ Failed to create workflow", err=True)
                click.echo(f"  Error: {e.stderr}", err=True)
                click.echo(f"\nWorkflow JSON saved to: {temp_file}")
                click.echo(
                    "You can manually create it with: databricks jobs create --json-file <file>"
                )
                sys.exit(1)

            except FileNotFoundError:
                click.echo(
                    "✗ Databricks CLI not found. Please install: pip install databricks-cli",
                    err=True,
                )
                sys.exit(1)

            finally:
                # Clean up temp file
                Path(temp_file).unlink(missing_ok=True)

    except Exception as e:
        click.echo(f"✗ Failed to create workflow: {e}", err=True)
        import traceback

        traceback.print_exc()
        sys.exit(1)


@databricks.command()
@click.option(
    "--notebook-path",
    default="kdf/databricks/notebooks/run_kdf_pipeline.py",
    help="Path to KDF runner notebook",
)
@click.option(
    "--workspace-path",
    default="/Workspace/kdf/notebooks",
    help="Databricks workspace path to upload to",
)
def upload_notebook(notebook_path: str, workspace_path: str):
    """
    Upload KDF runner notebook to Databricks workspace.

    Example:
        kdf databricks upload-notebook --workspace-path /Workspace/kdf/notebooks
    """
    notebook_file = Path(notebook_path)

    if not notebook_file.exists():
        click.echo(f"✗ Notebook not found: {notebook_path}", err=True)
        sys.exit(1)

    click.echo(f"Uploading notebook to Databricks workspace...")
    click.echo(f"  Source: {notebook_path}")
    click.echo(f"  Destination: {workspace_path}")

    # Use databricks CLI to upload
    cmd = [
        "databricks",
        "workspace",
        "import",
        str(notebook_file),
        workspace_path,
        "--language",
        "PYTHON",
        "--format",
        "SOURCE",
        "--overwrite",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        click.echo(f"✓ Notebook uploaded successfully")
        click.echo(f"  Workspace path: {workspace_path}")

    except subprocess.CalledProcessError as e:
        click.echo(f"✗ Failed to upload notebook", err=True)
        click.echo(f"  Error: {e.stderr}", err=True)
        sys.exit(1)

    except FileNotFoundError:
        click.echo(
            "✗ Databricks CLI not found. Please install: pip install databricks-cli",
            err=True,
        )
        sys.exit(1)


@databricks.command()
@click.option(
    "--dbfs-path",
    default="/kdf/wheels",
    help="DBFS path to upload wheel to",
)
def upload_kdf(dbfs_path: str):
    """
    Build and upload KDF wheel to DBFS.

    This builds a wheel from the current KDF installation and uploads it
    to DBFS for use in Databricks clusters.

    Example:
        kdf databricks upload-kdf --dbfs-path /kdf/wheels
    """
    click.echo(f"Building KDF wheel...")

    # Build wheel
    try:
        import tempfile
        import shutil

        with tempfile.TemporaryDirectory() as temp_dir:
            # Build wheel using pip
            cmd = ["pip", "wheel", ".", "--wheel-dir", temp_dir, "--no-deps"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, check=True, cwd="."
            )

            # Find the wheel file
            wheel_files = list(Path(temp_dir).glob("*.whl"))
            if not wheel_files:
                click.echo(f"✗ No wheel file generated", err=True)
                sys.exit(1)

            wheel_file = wheel_files[0]
            click.echo(f"✓ Wheel built: {wheel_file.name}")

            # Upload to DBFS
            dbfs_destination = f"dbfs:{dbfs_path}/{wheel_file.name}"
            click.echo(f"\nUploading to Databricks...")
            click.echo(f"  Destination: {dbfs_destination}")

            cmd = [
                "databricks",
                "fs",
                "cp",
                str(wheel_file),
                dbfs_destination,
                "--overwrite",
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            click.echo(f"✓ KDF wheel uploaded successfully")
            click.echo(f"\nTo install in your Databricks cluster:")
            click.echo(f"  pip install {dbfs_destination}")

    except subprocess.CalledProcessError as e:
        click.echo(f"✗ Command failed", err=True)
        click.echo(f"  Error: {e.stderr}", err=True)
        sys.exit(1)

    except Exception as e:
        click.echo(f"✗ Failed: {e}", err=True)
        sys.exit(1)


@databricks.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option(
    "--workflow-name",
    help="Databricks workflow name (defaults to config name)",
)
@click.option(
    "--schedule",
    help="Cron schedule (e.g., '0 0 2 * * ?' for daily at 2am)",
)
@click.option(
    "--notification-emails",
    help="Comma-separated email addresses for failure notifications",
)
def deploy(
    config_file: str,
    workflow_name: Optional[str],
    schedule: Optional[str],
    notification_emails: Optional[str],
):
    """
    Complete deployment: upload config and create workflow.

    This is a convenience command that:
    1. Uploads the config to DBFS
    2. Creates the Databricks workflow

    Example:
        kdf databricks deploy medallion.yaml \\
            --schedule "0 0 2 * * ?" \\
            --notification-emails team@company.com
    """
    config_path = Path(config_file)
    dbfs_config_path = f"dbfs:/kdf/configs/{config_path.name}"

    click.echo("="*80)
    click.echo("KDF Databricks Deployment")
    click.echo("="*80)

    # Step 1: Upload config
    click.echo("\n[1/2] Uploading config to DBFS...")
    ctx = click.get_current_context()
    ctx.invoke(
        upload_config,
        config_file=config_file,
        dbfs_path="/kdf/configs",
        overwrite=True,
    )

    # Step 2: Create workflow
    click.echo("\n[2/2] Creating Databricks workflow...")
    ctx.invoke(
        create_workflow,
        config_file=config_file,
        workflow_name=workflow_name,
        config_path=dbfs_config_path,
        schedule=schedule,
        notification_emails=notification_emails,
        output=None,
    )

    click.echo("\n" + "="*80)
    click.echo("✓ Deployment complete!")
    click.echo("="*80)
