#!/usr/bin/env python3
"""
KDF Databricks Deployment Automation Script

This script automates the deployment of KDF pipelines to Databricks.
Suitable for CI/CD pipelines and automated deployments.

Usage:
    python deploy_to_databricks.py --config my_pipeline.yaml --env production

Features:
    - Uploads config to DBFS
    - Creates/updates Databricks workflow
    - Supports multiple environments
    - Validates before deployment
    - Provides detailed logging
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from kdf.core.config import PipelineConfig, MedallionPipelineConfig
from kdf.databricks.workflow_builder import create_medallion_workflow_from_config, WorkflowBuilder, ClusterConfig


class Colors:
    """ANSI color codes"""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color


def log_info(message: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ {message}{Colors.NC}")


def log_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def log_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.NC}")


def log_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.NC}", file=sys.stderr)


def run_command(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    """Run shell command with error handling"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        log_error(f"Command failed: {' '.join(cmd)}")
        log_error(f"Error: {e.stderr}")
        raise


def check_databricks_cli() -> bool:
    """Check if Databricks CLI is installed and configured"""
    log_info("Checking Databricks CLI...")

    # Check if CLI is installed
    result = run_command(["which", "databricks"], check=False)
    if result.returncode != 0:
        log_error("Databricks CLI not found. Install with: pip install databricks-cli")
        return False

    # Check if configured
    result = run_command(["databricks", "workspace", "ls", "/"], check=False)
    if result.returncode != 0:
        log_error("Databricks CLI not configured. Run: databricks configure --token")
        return False

    log_success("Databricks CLI configured")
    return True


def validate_config(config_path: Path) -> str:
    """Validate KDF config and return type"""
    log_info(f"Validating config: {config_path}")

    if not config_path.exists():
        log_error(f"Config file not found: {config_path}")
        sys.exit(1)

    # Try to load as medallion config
    try:
        config = MedallionPipelineConfig.from_yaml(str(config_path))
        log_success(f"Valid medallion config: {config.name} ({len(config.pipelines)} pipelines)")
        return "medallion"
    except Exception:
        pass

    # Try to load as single pipeline config
    try:
        config = PipelineConfig.from_yaml(str(config_path))
        log_success(f"Valid pipeline config: {config.name}")
        return "single"
    except Exception as e:
        log_error(f"Invalid config: {e}")
        sys.exit(1)


def upload_config(config_path: Path, env: str) -> str:
    """Upload config to DBFS"""
    dbfs_path = f"/kdf/configs/{env}"
    dbfs_file = f"dbfs:{dbfs_path}/{config_path.name}"

    log_info(f"Uploading config to {dbfs_file}...")

    # Create directory if it doesn't exist
    run_command(["databricks", "fs", "mkdirs", f"dbfs:{dbfs_path}"])

    # Upload file
    run_command([
        "databricks", "fs", "cp",
        str(config_path),
        dbfs_file,
        "--overwrite"
    ])

    log_success(f"Config uploaded to {dbfs_file}")
    return dbfs_file


def create_workflow(
    config_path: Path,
    config_type: str,
    dbfs_config_path: str,
    workflow_name: Optional[str],
    env: str,
    schedule: Optional[str],
    emails: Optional[str]
) -> Dict[str, Any]:
    """Create workflow JSON"""
    log_info("Creating workflow JSON...")

    if not workflow_name:
        config_name = config_path.stem
        workflow_name = f"{env.upper()} - {config_name}"

    notification_emails = emails.split(",") if emails else None

    if config_type == "medallion":
        config = MedallionPipelineConfig.from_yaml(str(config_path))
        workflow_json = create_medallion_workflow_from_config(
            medallion_config=config,
            workflow_name=workflow_name,
            config_path=dbfs_config_path,
            schedule_cron=schedule,
            notification_emails=notification_emails
        )
    else:
        config = PipelineConfig.from_yaml(str(config_path))
        builder = WorkflowBuilder(name=workflow_name)

        builder.add_cluster(
            "kdf_cluster",
            ClusterConfig(
                num_workers=4,
                spark_conf={
                    "spark.databricks.delta.preview.enabled": "true",
                    "spark.sql.adaptive.enabled": "true",
                },
                custom_tags={
                    "framework": "kdf",
                    "environment": env,
                }
            )
        )

        builder.add_single_pipeline_task(
            task_key="run_pipeline",
            config_path=dbfs_config_path,
            cluster_key="kdf_cluster",
            description=f"Run {config.name}"
        )

        if schedule:
            builder.set_schedule(schedule)

        if notification_emails:
            builder.set_email_notifications(on_failure=notification_emails)

        workflow_json = builder.build()

    log_success(f"Workflow created: {workflow_name}")
    return workflow_json


def deploy_workflow(workflow_json: Dict[str, Any], dry_run: bool = False) -> Optional[str]:
    """Deploy workflow to Databricks"""
    if dry_run:
        log_warning("DRY RUN: Would create the following workflow:")
        print(json.dumps(workflow_json, indent=2))
        return None

    log_info("Deploying workflow to Databricks...")

    # Write to temp file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(workflow_json, f, indent=2)
        temp_file = f.name

    try:
        # Create workflow
        result = run_command([
            "databricks", "jobs", "create",
            "--json-file", temp_file
        ])

        # Parse job ID from response
        response = json.loads(result.stdout)
        job_id = response.get("job_id")

        log_success(f"Workflow created successfully!")
        log_success(f"Job ID: {job_id}")

        return job_id

    finally:
        # Clean up temp file
        Path(temp_file).unlink(missing_ok=True)


def trigger_workflow(job_id: str, wait: bool = False):
    """Trigger workflow run"""
    log_info(f"Triggering workflow run for job {job_id}...")

    cmd = ["databricks", "jobs", "run-now", "--job-id", job_id]
    result = run_command(cmd)

    response = json.loads(result.stdout)
    run_id = response.get("run_id")

    log_success(f"Workflow triggered: Run ID {run_id}")

    if wait:
        log_info("Waiting for workflow to complete...")
        # Poll for completion
        import time
        while True:
            result = run_command([
                "databricks", "runs", "get",
                "--run-id", str(run_id)
            ])
            response = json.loads(result.stdout)
            state = response.get("state", {})
            life_cycle_state = state.get("life_cycle_state")

            if life_cycle_state in ["TERMINATED", "SKIPPED", "INTERNAL_ERROR"]:
                result_state = state.get("result_state")
                if result_state == "SUCCESS":
                    log_success("Workflow completed successfully!")
                else:
                    log_error(f"Workflow failed with state: {result_state}")
                    sys.exit(1)
                break

            time.sleep(10)


def main():
    parser = argparse.ArgumentParser(
        description="Deploy KDF pipeline to Databricks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Deploy to production with schedule
  python deploy_to_databricks.py \\
    --config medallion.yaml \\
    --env production \\
    --schedule "0 0 2 * * ?" \\
    --emails team@company.com

  # Dry run for staging
  python deploy_to_databricks.py \\
    --config pipeline.yaml \\
    --env staging \\
    --dry-run

  # Deploy and trigger immediately
  python deploy_to_databricks.py \\
    --config pipeline.yaml \\
    --env dev \\
    --trigger \\
    --wait
        """
    )

    parser.add_argument(
        "--config",
        required=True,
        type=Path,
        help="Path to KDF pipeline config YAML"
    )

    parser.add_argument(
        "--env",
        default="production",
        choices=["dev", "staging", "production"],
        help="Deployment environment"
    )

    parser.add_argument(
        "--workflow-name",
        help="Databricks workflow name (defaults to <env> - <config_name>)"
    )

    parser.add_argument(
        "--schedule",
        help="Cron schedule (e.g., '0 0 2 * * ?' for daily at 2am)"
    )

    parser.add_argument(
        "--emails",
        help="Comma-separated notification emails"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate workflow JSON without deploying"
    )

    parser.add_argument(
        "--trigger",
        action="store_true",
        help="Trigger workflow run after creation"
    )

    parser.add_argument(
        "--wait",
        action="store_true",
        help="Wait for triggered run to complete (requires --trigger)"
    )

    args = parser.parse_args()

    print(f"{Colors.GREEN}╔═══════════════════════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.GREEN}║     KDF Databricks Deployment                         ║{Colors.NC}")
    print(f"{Colors.GREEN}╚═══════════════════════════════════════════════════════╝{Colors.NC}")
    print()

    # Check prerequisites
    if not check_databricks_cli():
        sys.exit(1)

    # Validate config
    config_type = validate_config(args.config)

    # Upload config
    dbfs_config_path = upload_config(args.config, args.env)

    # Create workflow
    workflow_json = create_workflow(
        config_path=args.config,
        config_type=config_type,
        dbfs_config_path=dbfs_config_path,
        workflow_name=args.workflow_name,
        env=args.env,
        schedule=args.schedule,
        emails=args.emails
    )

    # Deploy workflow
    job_id = deploy_workflow(workflow_json, dry_run=args.dry_run)

    if job_id:
        print()
        print(f"{Colors.GREEN}╔═══════════════════════════════════════════════════════╗{Colors.NC}")
        print(f"{Colors.GREEN}║     Deployment Summary                                ║{Colors.NC}")
        print(f"{Colors.GREEN}╠═══════════════════════════════════════════════════════╣{Colors.NC}")
        print(f"{Colors.GREEN}║  Job ID: {job_id:<45}║{Colors.NC}")
        print(f"{Colors.GREEN}║  Environment: {args.env:<40}║{Colors.NC}")
        print(f"{Colors.GREEN}║  Config: {dbfs_config_path:<43}║{Colors.NC}")
        print(f"{Colors.GREEN}╚═══════════════════════════════════════════════════════╝{Colors.NC}")
        print()

        # Trigger if requested
        if args.trigger:
            trigger_workflow(job_id, wait=args.wait)

    elif not args.dry_run:
        log_error("Failed to deploy workflow")
        sys.exit(1)


if __name__ == "__main__":
    main()
