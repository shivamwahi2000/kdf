"""Tests for data models."""

from datetime import datetime
from kdf.core.models import (
    PipelineRun,
    PipelineStatus,
    QualityResult,
    QualityStatus,
    SchemaChange,
    SchemaChangeType,
)


def test_pipeline_run():
    """Test pipeline run model."""
    run = PipelineRun(
        run_id="test_run_001",
        pipeline_name="test_pipeline",
        status=PipelineStatus.SUCCESS,
        start_time=datetime(2026, 9, 18, 10, 0, 0),
        records_read=1000,
        records_written=950,
    )

    assert run.run_id == "test_run_001"
    assert run.status == PipelineStatus.SUCCESS
    assert run.records_read == 1000


def test_quality_result():
    """Test quality result model."""
    result = QualityResult(
        check_name="not_null",
        status=QualityStatus.PASSED,
        column="customer_id",
        violations=0,
        total_records=1000,
    )

    assert result.check_name == "not_null"
    assert result.status == QualityStatus.PASSED
    assert result.violations == 0


def test_schema_change():
    """Test schema change model."""
    change = SchemaChange(
        column_name="order_total",
        change_type=SchemaChangeType.BREAKING,
        old_type="INTEGER",
        new_type="STRING",
        description="Type changed from INTEGER to STRING",
    )

    assert change.column_name == "order_total"
    assert change.change_type == SchemaChangeType.BREAKING
