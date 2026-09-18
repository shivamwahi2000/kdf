"""Tests for configuration module."""

import pytest
from kdf.core.config import PipelineConfig, SourceConfig, TargetConfig
from kdf.core.exceptions import ConfigurationError


def test_basic_pipeline_config():
    """Test basic pipeline configuration."""
    config = PipelineConfig(
        name="test_pipeline",
        source=SourceConfig(type="postgres", table="orders"),
        target=TargetConfig(path="/data/orders"),
    )

    assert config.name == "test_pipeline"
    assert config.source.type == "postgres"
    assert config.target.path == "/data/orders"


def test_config_validation():
    """Test configuration validation."""
    config = PipelineConfig(
        name="test_pipeline",
        source=SourceConfig(type="postgres", table="orders"),
        target=TargetConfig(path="/data/orders"),
    )

    issues = config.validate_config()
    assert isinstance(issues, list)


def test_empty_name_validation():
    """Test that empty name is rejected."""
    with pytest.raises(Exception):
        PipelineConfig(
            name="",
            source=SourceConfig(type="postgres", table="orders"),
            target=TargetConfig(path="/data/orders"),
        )
