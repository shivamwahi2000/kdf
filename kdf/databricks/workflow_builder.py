"""
Databricks Workflow Builder

Utilities for creating Databricks Workflows programmatically from KDF pipeline configs.
"""

import json
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from dataclasses import dataclass, field, asdict

from kdf.core.config import PipelineConfig, MedallionPipelineConfig
from kdf.core.models import ExecutionMode


@dataclass
class ClusterConfig:
    """Configuration for a Databricks cluster."""

    spark_version: str = "13.3.x-scala2.12"
    node_type_id: str = "i3.xlarge"
    num_workers: Optional[int] = None
    autoscale_min_workers: Optional[int] = None
    autoscale_max_workers: Optional[int] = None
    spark_conf: Dict[str, str] = field(default_factory=dict)
    custom_tags: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Databricks API format."""
        cluster = {
            "spark_version": self.spark_version,
            "node_type_id": self.node_type_id,
        }

        # Add workers or autoscale
        if self.autoscale_min_workers and self.autoscale_max_workers:
            cluster["autoscale"] = {
                "min_workers": self.autoscale_min_workers,
                "max_workers": self.autoscale_max_workers,
            }
        elif self.num_workers is not None:
            cluster["num_workers"] = self.num_workers

        # Add configs
        if self.spark_conf:
            cluster["spark_conf"] = self.spark_conf

        if self.custom_tags:
            cluster["custom_tags"] = self.custom_tags

        return cluster


@dataclass
class TaskConfig:
    """Configuration for a Databricks task."""

    task_key: str
    description: str
    notebook_path: str
    base_parameters: Dict[str, str]
    job_cluster_key: str
    depends_on: List[str] = field(default_factory=list)
    timeout_seconds: int = 3600
    max_retries: int = 2
    retry_on_timeout: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Databricks API format."""
        task = {
            "task_key": self.task_key,
            "description": self.description,
            "notebook_task": {
                "notebook_path": self.notebook_path,
                "base_parameters": self.base_parameters,
                "source": "WORKSPACE",
            },
            "job_cluster_key": self.job_cluster_key,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }

        if self.retry_on_timeout:
            task["retry_on_timeout"] = True

        if self.depends_on:
            task["depends_on"] = [{"task_key": dep} for dep in self.depends_on]

        return task


@dataclass
class ScheduleConfig:
    """Configuration for workflow schedule."""

    quartz_cron_expression: str
    timezone_id: str = "UTC"
    pause_status: str = "UNPAUSED"

    def to_dict(self) -> Dict[str, str]:
        """Convert to Databricks API format."""
        return {
            "quartz_cron_expression": self.quartz_cron_expression,
            "timezone_id": self.timezone_id,
            "pause_status": self.pause_status,
        }


@dataclass
class EmailNotifications:
    """Email notification configuration."""

    on_failure: List[str] = field(default_factory=list)
    on_success: List[str] = field(default_factory=list)
    on_start: List[str] = field(default_factory=list)
    no_alert_for_skipped_runs: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Databricks API format."""
        notifications = {}

        if self.on_failure:
            notifications["on_failure"] = self.on_failure
        if self.on_success:
            notifications["on_success"] = self.on_success
        if self.on_start:
            notifications["on_start"] = self.on_start

        notifications["no_alert_for_skipped_runs"] = self.no_alert_for_skipped_runs

        return notifications


class WorkflowBuilder:
    """Builder for creating Databricks Workflows from KDF configs."""

    def __init__(
        self,
        name: str,
        notebook_path: str = "/Workspace/kdf/notebooks/run_kdf_pipeline",
        metadata_path: str = "/kdf/metadata",
    ):
        """
        Initialize workflow builder.

        Args:
            name: Workflow name
            notebook_path: Path to KDF runner notebook in Databricks workspace
            metadata_path: Path to KDF metadata in DBFS
        """
        self.name = name
        self.notebook_path = notebook_path
        self.metadata_path = metadata_path

        self.tasks: List[TaskConfig] = []
        self.clusters: Dict[str, ClusterConfig] = {}
        self.schedule: Optional[ScheduleConfig] = None
        self.email_notifications: Optional[EmailNotifications] = None
        self.max_concurrent_runs: int = 1
        self.timeout_seconds: int = 7200

    def add_cluster(self, key: str, config: ClusterConfig) -> "WorkflowBuilder":
        """Add a cluster configuration."""
        self.clusters[key] = config
        return self

    def add_single_pipeline_task(
        self,
        task_key: str,
        config_path: str,
        cluster_key: str,
        description: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
        timeout_seconds: int = 3600,
        max_retries: int = 2,
    ) -> "WorkflowBuilder":
        """
        Add a task for running a single pipeline.

        Args:
            task_key: Unique task identifier
            config_path: DBFS path to pipeline config YAML
            cluster_key: Job cluster key to use
            description: Task description
            depends_on: List of task keys this task depends on
            timeout_seconds: Task timeout
            max_retries: Max retry attempts
        """
        task = TaskConfig(
            task_key=task_key,
            description=description or f"Run KDF pipeline: {task_key}",
            notebook_path=self.notebook_path,
            base_parameters={
                "config_path": config_path,
                "metadata_path": self.metadata_path,
                "config_type": "single",
            },
            job_cluster_key=cluster_key,
            depends_on=depends_on or [],
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

        self.tasks.append(task)
        return self

    def add_medallion_pipeline_task(
        self,
        task_key: str,
        config_path: str,
        pipeline_name: str,
        cluster_key: str,
        description: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
        timeout_seconds: int = 3600,
        max_retries: int = 2,
    ) -> "WorkflowBuilder":
        """
        Add a task for running a specific pipeline from a medallion config.

        Args:
            task_key: Unique task identifier
            config_path: DBFS path to medallion config YAML
            pipeline_name: Name of specific pipeline to run
            cluster_key: Job cluster key to use
            description: Task description
            depends_on: List of task keys this task depends on
            timeout_seconds: Task timeout
            max_retries: Max retry attempts
        """
        task = TaskConfig(
            task_key=task_key,
            description=description or f"Run {pipeline_name}",
            notebook_path=self.notebook_path,
            base_parameters={
                "config_path": config_path,
                "metadata_path": self.metadata_path,
                "config_type": "medallion",
                "pipeline_name": pipeline_name,
            },
            job_cluster_key=cluster_key,
            depends_on=depends_on or [],
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

        self.tasks.append(task)
        return self

    def set_schedule(
        self,
        cron_expression: str,
        timezone: str = "UTC",
        paused: bool = False,
    ) -> "WorkflowBuilder":
        """
        Set workflow schedule.

        Args:
            cron_expression: Quartz cron expression
            timezone: Timezone ID (e.g., "UTC", "America/Los_Angeles")
            paused: Whether schedule is paused
        """
        self.schedule = ScheduleConfig(
            quartz_cron_expression=cron_expression,
            timezone_id=timezone,
            pause_status="PAUSED" if paused else "UNPAUSED",
        )
        return self

    def set_email_notifications(
        self,
        on_failure: Optional[List[str]] = None,
        on_success: Optional[List[str]] = None,
        on_start: Optional[List[str]] = None,
    ) -> "WorkflowBuilder":
        """Set email notifications."""
        self.email_notifications = EmailNotifications(
            on_failure=on_failure or [],
            on_success=on_success or [],
            on_start=on_start or [],
        )
        return self

    def set_concurrency(self, max_concurrent_runs: int) -> "WorkflowBuilder":
        """Set maximum concurrent workflow runs."""
        self.max_concurrent_runs = max_concurrent_runs
        return self

    def set_timeout(self, timeout_seconds: int) -> "WorkflowBuilder":
        """Set overall workflow timeout."""
        self.timeout_seconds = timeout_seconds
        return self

    def build(self) -> Dict[str, Any]:
        """Build workflow JSON."""
        if not self.tasks:
            raise ValueError("Workflow must have at least one task")

        if not self.clusters:
            raise ValueError("Workflow must have at least one cluster")

        workflow = {
            "name": self.name,
            "tasks": [task.to_dict() for task in self.tasks],
            "job_clusters": [
                {"job_cluster_key": key, "new_cluster": config.to_dict()}
                for key, config in self.clusters.items()
            ],
            "format": "MULTI_TASK",
            "max_concurrent_runs": self.max_concurrent_runs,
            "timeout_seconds": self.timeout_seconds,
        }

        if self.schedule:
            workflow["schedule"] = self.schedule.to_dict()

        if self.email_notifications:
            workflow["email_notifications"] = self.email_notifications.to_dict()

        return workflow

    def to_json(self, indent: int = 2) -> str:
        """Convert workflow to JSON string."""
        return json.dumps(self.build(), indent=indent)

    def save(self, path: Union[str, Path]) -> None:
        """Save workflow to JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w") as f:
            f.write(self.to_json())


def create_medallion_workflow_from_config(
    medallion_config: MedallionPipelineConfig,
    workflow_name: Optional[str] = None,
    config_path: str = "dbfs:/kdf/configs/medallion.yaml",
    cluster_config: Optional[ClusterConfig] = None,
    schedule_cron: Optional[str] = None,
    notification_emails: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Create a Databricks workflow from a KDF medallion config.

    This automatically creates tasks with proper dependencies based on the
    medallion config's execution order.

    Args:
        medallion_config: KDF medallion pipeline configuration
        workflow_name: Databricks workflow name (defaults to config name)
        config_path: DBFS path where config will be uploaded
        cluster_config: Cluster configuration (uses defaults if not provided)
        schedule_cron: Optional cron schedule
        notification_emails: Email addresses for notifications

    Returns:
        Workflow JSON dictionary
    """
    builder = WorkflowBuilder(
        name=workflow_name or f"KDF {medallion_config.name}",
    )

    # Add default cluster if not provided
    if not cluster_config:
        cluster_config = ClusterConfig(
            num_workers=4,
            spark_conf={
                "spark.databricks.delta.preview.enabled": "true",
                "spark.databricks.delta.optimizeWrite.enabled": "true",
                "spark.sql.adaptive.enabled": "true",
            },
            custom_tags={
                "framework": "kdf",
                "version": "0.1",
                "architecture": "medallion",
            },
        )

    builder.add_cluster("kdf_cluster", cluster_config)

    # Get execution order
    execution_order = medallion_config.get_execution_order()

    # Track dependencies
    task_key_map = {}

    # Create tasks for each pipeline
    for stage in execution_order:
        for pipeline_name in stage:
            # Find pipeline config
            pipeline_config = next(
                p for p in medallion_config.pipelines if p.name == pipeline_name
            )

            # Determine dependencies from config
            depends_on = [
                task_key_map[dep]
                for dep in pipeline_config.depends_on
                if dep in task_key_map
            ]

            # Create task
            task_key = f"task_{pipeline_name}"
            task_key_map[pipeline_name] = task_key

            description = pipeline_name
            if pipeline_config.medallion:
                layer = pipeline_config.medallion.layer.value.upper()
                description = f"{layer} layer: {pipeline_name}"

            # Determine timeout based on execution mode
            timeout = 3600  # Default 1 hour
            max_retries = 2

            if pipeline_config.execution_mode == ExecutionMode.STREAMING:
                timeout = 0  # No timeout for streaming
                max_retries = 0

            builder.add_medallion_pipeline_task(
                task_key=task_key,
                config_path=config_path,
                pipeline_name=pipeline_name,
                cluster_key="kdf_cluster",
                description=description,
                depends_on=depends_on,
                timeout_seconds=timeout,
                max_retries=max_retries,
            )

    # Add schedule if provided
    if schedule_cron:
        builder.set_schedule(schedule_cron)

    # Add notifications if provided
    if notification_emails:
        builder.set_email_notifications(on_failure=notification_emails)

    return builder.build()


# Predefined cluster configurations
DEFAULT_BATCH_CLUSTER = ClusterConfig(
    num_workers=4,
    spark_conf={
        "spark.databricks.delta.preview.enabled": "true",
        "spark.databricks.delta.optimizeWrite.enabled": "true",
        "spark.sql.adaptive.enabled": "true",
    },
    custom_tags={"framework": "kdf", "cluster_type": "batch"},
)

DEFAULT_STREAMING_CLUSTER = ClusterConfig(
    autoscale_min_workers=2,
    autoscale_max_workers=8,
    spark_conf={
        "spark.databricks.delta.preview.enabled": "true",
        "spark.streaming.backpressure.enabled": "true",
        "spark.sql.streaming.stateStore.maintenanceInterval": "300s",
    },
    custom_tags={"framework": "kdf", "cluster_type": "streaming"},
)

# Common cron schedules
SCHEDULE_HOURLY = "0 0 * * * ?"
SCHEDULE_DAILY_2AM = "0 0 2 * * ?"
SCHEDULE_EVERY_15MIN = "0 */15 * * * ?"
SCHEDULE_EVERY_5MIN = "0 */5 * * * ?"
