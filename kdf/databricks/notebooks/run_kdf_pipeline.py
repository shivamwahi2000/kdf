# Databricks notebook source
# MAGIC %md
# MAGIC # KDF Pipeline Runner for Databricks Workflows
# MAGIC
# MAGIC This notebook runs KDF pipelines in Databricks Workflows.
# MAGIC
# MAGIC **Parameters:**
# MAGIC - `config_path`: Path to pipeline YAML config (required)
# MAGIC - `metadata_path`: Path to metadata Delta table (optional, default: /kdf/metadata)
# MAGIC - `pipeline_name`: Specific pipeline to run for medallion configs (optional)
# MAGIC - `config_type`: Type of config - "single" or "medallion" (optional, auto-detected)
# MAGIC
# MAGIC **Example Usage:**
# MAGIC ```
# MAGIC config_path: /dbfs/kdf/configs/medallion_orders.yaml
# MAGIC metadata_path: /kdf/metadata
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup and Imports

# COMMAND ----------

import sys
import os
import json
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

# Add KDF to path if installed via wheel
try:
    from kdf.core.pipeline import Pipeline
    from kdf.core.config import PipelineConfig, MedallionPipelineConfig
    from kdf.core.context import ExecutionContext
    from kdf.core.exceptions import KDFError, PipelineExecutionError
    from kdf.bootstrap import bootstrap_registries
except ImportError:
    print("ERROR: KDF not found. Please install KDF wheel file first.")
    print("Run: pip install /dbfs/kdf/wheels/kdf-0.1.0-py3-none-any.whl")
    dbutils.notebook.exit(json.dumps({
        "status": "ERROR",
        "error": "KDF not installed",
        "message": "Please install KDF wheel file"
    }))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Widget Parameters

# COMMAND ----------

# Create widgets for parameters
dbutils.widgets.text("config_path", "", "Pipeline Config Path")
dbutils.widgets.text("metadata_path", "/kdf/metadata", "Metadata Path")
dbutils.widgets.text("pipeline_name", "", "Pipeline Name (for medallion)")
dbutils.widgets.dropdown("config_type", "auto", ["auto", "single", "medallion"], "Config Type")

# Get parameter values
config_path = dbutils.widgets.get("config_path")
metadata_path = dbutils.widgets.get("metadata_path")
pipeline_name = dbutils.widgets.get("pipeline_name")
config_type = dbutils.widgets.get("config_type")

# Validate required parameters
if not config_path:
    error_msg = "config_path parameter is required"
    print(f"ERROR: {error_msg}")
    dbutils.notebook.exit(json.dumps({
        "status": "ERROR",
        "error": "missing_parameter",
        "message": error_msg
    }))

print(f"Configuration:")
print(f"  Config Path: {config_path}")
print(f"  Metadata Path: {metadata_path}")
print(f"  Pipeline Name: {pipeline_name or '(all)'}")
print(f"  Config Type: {config_type}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

def detect_config_type(config_path: str) -> str:
    """Detect if config is single pipeline or medallion."""
    try:
        with open(config_path.replace("dbfs:", "/dbfs"), "r") as f:
            import yaml
            config_data = yaml.safe_load(f)

        if "pipelines" in config_data:
            return "medallion"
        else:
            return "single"
    except Exception as e:
        print(f"WARNING: Could not detect config type: {e}")
        return "single"

def format_duration(seconds: float) -> str:
    """Format duration in human readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def create_result_dict(
    status: str,
    config_path: str,
    execution_time: float,
    context: Optional[ExecutionContext] = None,
    error: Optional[str] = None,
    error_details: Optional[str] = None
) -> Dict[str, Any]:
    """Create standardized result dictionary."""
    result = {
        "status": status,
        "config_path": config_path,
        "execution_time_seconds": execution_time,
        "execution_time_formatted": format_duration(execution_time),
        "timestamp": datetime.utcnow().isoformat()
    }

    if context:
        result["pipeline_name"] = context.pipeline_name
        result["run_id"] = context.run_id
        result["records_read"] = context.metrics.get("records_read", 0)
        result["records_written"] = context.metrics.get("records_written", 0)
        result["metadata_table"] = f"{metadata_path}/pipeline_runs"

    if error:
        result["error"] = error
        if error_details:
            result["error_details"] = error_details

    return result

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Single Pipeline

# COMMAND ----------

def run_single_pipeline(config_path: str, metadata_path: str) -> Dict[str, Any]:
    """Run a single KDF pipeline."""
    print("\n" + "="*80)
    print("Running Single Pipeline")
    print("="*80)

    start_time = datetime.utcnow()

    try:
        # Bootstrap registries
        print("\n[1/4] Bootstrapping KDF registries...")
        bootstrap_registries()
        print("✓ Registries bootstrapped")

        # Load configuration
        print(f"\n[2/4] Loading pipeline configuration from {config_path}...")
        config = PipelineConfig.from_yaml(config_path.replace("dbfs:", "/dbfs"))
        print(f"✓ Configuration loaded: {config.name}")

        # Create pipeline
        print("\n[3/4] Creating pipeline...")
        pipeline = Pipeline(config)
        print(f"✓ Pipeline created: {config.name}")

        # Run pipeline
        print(f"\n[4/4] Running pipeline: {config.name}")
        print("-" * 80)
        context = pipeline.run(metadata_path=metadata_path)
        print("-" * 80)

        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()

        # Print summary
        print(f"\n✓ Pipeline completed successfully!")
        print(f"  Run ID: {context.run_id}")
        print(f"  Records Read: {context.metrics.get('records_read', 0):,}")
        print(f"  Records Written: {context.metrics.get('records_written', 0):,}")
        print(f"  Execution Time: {format_duration(execution_time)}")

        # Create result
        result = create_result_dict(
            status="SUCCESS",
            config_path=config_path,
            execution_time=execution_time,
            context=context
        )

        return result

    except KDFError as e:
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        error_details = traceback.format_exc()

        print(f"\n✗ Pipeline failed with KDF error: {str(e)}")
        print(f"\nError details:\n{error_details}")

        result = create_result_dict(
            status="FAILED",
            config_path=config_path,
            execution_time=execution_time,
            error=str(e),
            error_details=error_details
        )

        return result

    except Exception as e:
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        error_details = traceback.format_exc()

        print(f"\n✗ Pipeline failed with unexpected error: {str(e)}")
        print(f"\nError details:\n{error_details}")

        result = create_result_dict(
            status="FAILED",
            config_path=config_path,
            execution_time=execution_time,
            error=f"Unexpected error: {str(e)}",
            error_details=error_details
        )

        return result

# COMMAND ----------

# MAGIC %md
# MAGIC ## Run Medallion Workflow

# COMMAND ----------

def run_medallion_workflow(
    config_path: str,
    metadata_path: str,
    pipeline_name: Optional[str] = None
) -> Dict[str, Any]:
    """Run a medallion workflow (multi-pipeline)."""
    print("\n" + "="*80)
    print("Running Medallion Workflow")
    print("="*80)

    start_time = datetime.utcnow()

    try:
        # Bootstrap registries
        print("\n[1/5] Bootstrapping KDF registries...")
        bootstrap_registries()
        print("✓ Registries bootstrapped")

        # Load configuration
        print(f"\n[2/5] Loading medallion configuration from {config_path}...")
        config = MedallionPipelineConfig.from_yaml(config_path.replace("dbfs:", "/dbfs"))
        print(f"✓ Configuration loaded: {config.name}")
        print(f"  Total Pipelines: {len(config.pipelines)}")

        # Filter pipeline if specified
        pipelines_to_run = config.pipelines
        if pipeline_name:
            pipelines_to_run = [p for p in config.pipelines if p.name == pipeline_name]
            if not pipelines_to_run:
                raise ValueError(f"Pipeline '{pipeline_name}' not found in config")
            print(f"  Filtering to run: {pipeline_name}")

        # Get execution order
        print(f"\n[3/5] Computing execution order...")
        execution_order = config.get_execution_order()
        total_stages = len(execution_order)
        print(f"✓ Execution order computed: {total_stages} stages")

        for stage_num, stage in enumerate(execution_order, 1):
            print(f"  Stage {stage_num}: {', '.join(stage)}")

        # Print medallion layers
        print(f"\n[4/5] Medallion layers:")
        layers = {}
        for p in config.pipelines:
            if p.medallion:
                layer = p.medallion.layer.value
                if layer not in layers:
                    layers[layer] = []
                layers[layer].append(p.name)

        for layer in ["bronze", "silver", "gold", "custom"]:
            if layer in layers:
                print(f"  {layer.upper()}: {', '.join(layers[layer])}")

        # Run pipelines
        print(f"\n[5/5] Running {len(pipelines_to_run)} pipeline(s)...")
        print("=" * 80)

        results = []
        overall_status = "SUCCESS"

        for stage_num, stage in enumerate(execution_order, 1):
            print(f"\n{'='*80}")
            print(f"Stage {stage_num}/{total_stages}")
            print('='*80)

            for pipeline_name_in_stage in stage:
                # Skip if not in filtered list
                pipeline_config = next(
                    (p for p in pipelines_to_run if p.name == pipeline_name_in_stage),
                    None
                )

                if not pipeline_config:
                    print(f"\nSkipping {pipeline_name_in_stage} (filtered out)")
                    continue

                print(f"\n→ {pipeline_name_in_stage}")
                if pipeline_config.medallion:
                    print(f"  Layer: {pipeline_config.medallion.layer.value}")
                print("-" * 80)

                try:
                    # Create and run pipeline
                    pipeline = Pipeline(pipeline_config)
                    context = pipeline.run(metadata_path=metadata_path)

                    print(f"✓ {pipeline_name_in_stage} completed successfully")
                    print(f"  Records Read: {context.metrics.get('records_read', 0):,}")
                    print(f"  Records Written: {context.metrics.get('records_written', 0):,}")

                    results.append({
                        "pipeline": pipeline_name_in_stage,
                        "status": "SUCCESS",
                        "run_id": context.run_id,
                        "records_read": context.metrics.get("records_read", 0),
                        "records_written": context.metrics.get("records_written", 0)
                    })

                except Exception as e:
                    error_msg = str(e)
                    print(f"✗ {pipeline_name_in_stage} failed: {error_msg}")

                    overall_status = "FAILED"
                    results.append({
                        "pipeline": pipeline_name_in_stage,
                        "status": "FAILED",
                        "error": error_msg
                    })

                    # Stop execution on failure
                    print("\n✗ Stopping workflow due to pipeline failure")
                    break

            # Stop if any pipeline failed
            if overall_status == "FAILED":
                break

        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()

        # Print summary
        print("\n" + "="*80)
        print("Workflow Summary")
        print("="*80)
        print(f"Status: {overall_status}")
        print(f"Execution Time: {format_duration(execution_time)}")
        print(f"\nPipeline Results:")

        for result in results:
            status_icon = "✓" if result["status"] == "SUCCESS" else "✗"
            print(f"  {status_icon} {result['pipeline']}: {result['status']}")
            if result["status"] == "SUCCESS":
                print(f"    Records: {result['records_read']:,} → {result['records_written']:,}")

        # Create result
        result = {
            "status": overall_status,
            "workflow_name": config.name,
            "config_path": config_path,
            "total_pipelines": len(pipelines_to_run),
            "total_stages": total_stages,
            "execution_time_seconds": execution_time,
            "execution_time_formatted": format_duration(execution_time),
            "timestamp": datetime.utcnow().isoformat(),
            "pipeline_results": results,
            "metadata_table": f"{metadata_path}/pipeline_runs"
        }

        return result

    except Exception as e:
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        error_details = traceback.format_exc()

        print(f"\n✗ Workflow failed: {str(e)}")
        print(f"\nError details:\n{error_details}")

        result = {
            "status": "FAILED",
            "config_path": config_path,
            "execution_time_seconds": execution_time,
            "execution_time_formatted": format_duration(execution_time),
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e),
            "error_details": error_details
        }

        return result

# COMMAND ----------

# MAGIC %md
# MAGIC ## Main Execution

# COMMAND ----------

# Detect config type if auto
if config_type == "auto":
    config_type = detect_config_type(config_path)
    print(f"\nAuto-detected config type: {config_type}")

# Run appropriate workflow
if config_type == "medallion":
    result = run_medallion_workflow(config_path, metadata_path, pipeline_name or None)
else:
    result = run_single_pipeline(config_path, metadata_path)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Return Result

# COMMAND ----------

# Print final result
print("\n" + "="*80)
print("Final Result")
print("="*80)
print(json.dumps(result, indent=2))

# Exit with result (for Databricks Workflows)
dbutils.notebook.exit(json.dumps(result))
