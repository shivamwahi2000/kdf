"""Configuration management for KDF pipelines."""

import os
from typing import Any, Dict, List, Optional
import yaml
from pydantic import BaseModel, Field, field_validator

from kdf.core.exceptions import ConfigurationError
from kdf.core.models import ExecutionMode, MedallionConfig, PipelineDependency


class SourceConfig(BaseModel):
    """Source configuration."""
    type: str
    connection: Optional[str] = None
    database: Optional[str] = None
    schema: Optional[str] = None
    table: Optional[str] = None
    path: Optional[str] = None
    format: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class IngestionConfig(BaseModel):
    """Ingestion configuration."""
    skill: str
    column: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class SkillConfig(BaseModel):
    """Individual skill configuration."""
    name: str
    config: Dict[str, Any] = Field(default_factory=dict)


class QualityCheckConfig(BaseModel):
    """Data quality check configuration."""
    type: str
    columns: Optional[List[str]] = None
    column: Optional[str] = None
    threshold: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class TargetConfig(BaseModel):
    """Target configuration."""
    type: str = "delta"
    path: str
    mode: str = "append"
    partition_by: Optional[List[str]] = None
    options: Dict[str, Any] = Field(default_factory=dict)


class PipelineConfig(BaseModel):
    """Complete pipeline configuration."""
    name: str
    source: SourceConfig
    ingestion: Optional[IngestionConfig] = None
    skills: List[Dict[str, Any]] = Field(default_factory=list)
    quality: List[Dict[str, Any]] = Field(default_factory=list)
    target: TargetConfig
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Execution configuration
    execution_mode: ExecutionMode = ExecutionMode.BATCH
    trigger: Optional[str] = None  # For micro-batch/streaming (e.g., "5 minutes", "10 seconds")
    checkpoint_location: Optional[str] = None  # For streaming checkpoints

    # Medallion architecture
    medallion: Optional[MedallionConfig] = None

    # Pipeline dependencies
    depends_on: List[str] = Field(default_factory=list)  # List of pipeline names

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate pipeline name."""
        if not v or not v.strip():
            raise ValueError("Pipeline name cannot be empty")
        return v.strip()

    @classmethod
    def from_yaml(cls, path: str) -> "PipelineConfig":
        """Load configuration from YAML file."""
        if not os.path.exists(path):
            raise ConfigurationError(f"Configuration file not found: {path}")

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)

            if not data:
                raise ConfigurationError("Configuration file is empty")

            # Handle legacy 'pipeline' key
            if "pipeline" in data and "name" not in data:
                data["name"] = data.pop("pipeline")

            return cls(**data)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML: {e}")
        except Exception as e:
            raise ConfigurationError(f"Configuration error: {e}")

    def to_yaml(self, path: str) -> None:
        """Save configuration to YAML file."""
        try:
            with open(path, "w") as f:
                yaml.safe_dump(self.model_dump(exclude_none=True), f, default_flow_style=False)
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []

        # Validate source
        if self.source.type == "postgres":
            if not self.source.table:
                issues.append("PostgreSQL source requires 'table'")
        elif self.source.type == "s3":
            if not self.source.path:
                issues.append("S3 source requires 'path'")
            if not self.source.format:
                issues.append("S3 source requires 'format'")

        # Validate ingestion
        if self.ingestion and self.ingestion.skill == "incremental":
            if not self.ingestion.column:
                issues.append("Incremental ingestion requires 'column'")

        # Validate target
        if not self.target.path:
            issues.append("Target requires 'path'")

        return issues


class MedallionPipelineConfig(BaseModel):
    """Multi-pipeline configuration for medallion architecture."""
    name: str
    description: Optional[str] = None
    pipelines: List[PipelineConfig]

    @classmethod
    def from_yaml(cls, path: str) -> "MedallionPipelineConfig":
        """Load multi-pipeline configuration from YAML file."""
        if not os.path.exists(path):
            raise ConfigurationError(f"Configuration file not found: {path}")

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)

            if not data:
                raise ConfigurationError("Configuration file is empty")

            # Check if it's a multi-pipeline or single pipeline config
            if "pipelines" in data:
                return cls(**data)
            else:
                # Single pipeline - wrap in multi-pipeline config
                pipeline = PipelineConfig(**data)
                return cls(
                    name=pipeline.name,
                    pipelines=[pipeline]
                )

        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML: {e}")
        except Exception as e:
            raise ConfigurationError(f"Configuration error: {e}")

    def validate_dependencies(self) -> List[str]:
        """Validate pipeline dependencies form a valid DAG."""
        issues = []
        pipeline_names = {p.name for p in self.pipelines}

        for pipeline in self.pipelines:
            for dep in pipeline.depends_on:
                if dep not in pipeline_names:
                    issues.append(
                        f"Pipeline '{pipeline.name}' depends on '{dep}' which doesn't exist"
                    )

        # Check for circular dependencies (simple check)
        # TODO: Implement full cycle detection for production
        for pipeline in self.pipelines:
            if pipeline.name in pipeline.depends_on:
                issues.append(f"Pipeline '{pipeline.name}' has circular dependency on itself")

        return issues

    def get_execution_order(self) -> List[List[str]]:
        """Get pipeline execution order (topological sort).

        Returns:
            List of lists, where each inner list contains pipelines that can run in parallel
        """
        # Build dependency graph
        graph = {p.name: set(p.depends_on) for p in self.pipelines}
        result = []
        processed = set()

        while len(processed) < len(self.pipelines):
            # Find pipelines with no unprocessed dependencies
            ready = [
                name for name in graph
                if name not in processed and graph[name].issubset(processed)
            ]

            if not ready:
                # Circular dependency detected
                remaining = [name for name in graph if name not in processed]
                raise ConfigurationError(
                    f"Circular dependency detected among pipelines: {remaining}"
                )

            result.append(ready)
            processed.update(ready)

        return result
