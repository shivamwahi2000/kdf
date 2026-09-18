"""Medallion architecture CLI commands."""

import click
import sys
from kdf.core.config import MedallionPipelineConfig
from kdf.core.pipeline import Pipeline
from kdf.core.context import ExecutionContext
from kdf.metadata.runs import RunMetadataStore


@click.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--metadata-path", default="./kdf_metadata", help="Metadata storage path")
@click.option("--parallel", is_flag=True, help="Run independent pipelines in parallel")
def run_medallion(config_file: str, metadata_path: str, parallel: bool):
    """Run a medallion architecture (multi-pipeline) workflow.

    This command executes pipelines in dependency order, respecting the
    medallion architecture layers (Bronze → Silver → Gold).

    Example config:

    \b
    name: orders_medallion
    pipelines:
      - name: bronze_orders
        medallion:
          layer: bronze
        source:
          type: postgres
          table: orders
        target:
          path: /medallion/bronze/orders

      - name: silver_orders
        depends_on: [bronze_orders]
        medallion:
          layer: silver
        source:
          type: delta
          path: /medallion/bronze/orders
        skills:
          - deduplicate
        target:
          path: /medallion/silver/orders
    """
    try:
        # Load multi-pipeline configuration
        config = MedallionPipelineConfig.from_yaml(config_file)

        click.echo(f"Medallion Workflow: {config.name}")
        click.echo(f"Pipelines: {len(config.pipelines)}")

        # Validate dependencies
        dep_issues = config.validate_dependencies()
        if dep_issues:
            click.echo("✗ Dependency validation failed:", err=True)
            for issue in dep_issues:
                click.echo(f"  - {issue}", err=True)
            sys.exit(1)

        # Get execution order
        execution_order = config.get_execution_order()

        click.echo(f"\nExecution Plan ({len(execution_order)} stages):")
        for i, stage in enumerate(execution_order, 1):
            click.echo(f"  Stage {i}: {', '.join(stage)}")

        click.echo("\nStarting execution...\n")

        # Execute pipelines in order
        results = {}
        for stage_num, stage in enumerate(execution_order, 1):
            click.echo(f"Stage {stage_num}/{len(execution_order)}: {', '.join(stage)}")

            for pipeline_name in stage:
                # Find pipeline config
                pipeline_config = next(p for p in config.pipelines if p.name == pipeline_name)

                # Show layer info if available
                if pipeline_config.medallion:
                    click.echo(f"  → {pipeline_name} ({pipeline_config.medallion.layer.value} layer)")
                else:
                    click.echo(f"  → {pipeline_name}")

                # Create and run pipeline
                pipeline = Pipeline(pipeline_config)
                context = ExecutionContext(
                    config=pipeline_config,
                    metadata_path=metadata_path,
                )

                try:
                    result = pipeline.run(context)

                    # Save run metadata
                    store = RunMetadataStore(context.spark, metadata_path)
                    store.save_run(result.get_pipeline_run())

                    results[pipeline_name] = result

                    # Show results
                    click.echo(f"    ✓ Status: {result.status.value}")
                    click.echo(f"    ✓ Records read: {result.metrics.get('records_read', 'N/A')}")
                    click.echo(f"    ✓ Records written: {result.metrics.get('records_written', 'N/A')}")

                except Exception as e:
                    click.echo(f"    ✗ Failed: {e}", err=True)
                    results[pipeline_name] = None
                    sys.exit(1)

            click.echo()

        # Summary
        click.echo("✓ Medallion workflow completed successfully!")
        click.echo(f"\nTotal pipelines executed: {len(results)}")

    except Exception as e:
        click.echo(f"✗ Medallion workflow failed: {e}", err=True)
        sys.exit(1)


@click.command()
@click.argument("config_file", type=click.Path(exists=True))
def validate_medallion(config_file: str):
    """Validate a medallion architecture configuration."""
    try:
        config = MedallionPipelineConfig.from_yaml(config_file)

        click.echo(f"✓ Configuration valid: {config_file}")
        click.echo(f"\nWorkflow: {config.name}")
        click.echo(f"Pipelines: {len(config.pipelines)}")

        # Validate dependencies
        dep_issues = config.validate_dependencies()
        if dep_issues:
            click.echo("\n✗ Dependency issues:")
            for issue in dep_issues:
                click.echo(f"  - {issue}")
            sys.exit(1)

        # Show execution order
        execution_order = config.get_execution_order()
        click.echo(f"\nExecution order ({len(execution_order)} stages):")
        for i, stage in enumerate(execution_order, 1):
            click.echo(f"  Stage {i}: {', '.join(stage)}")

        # Show layer breakdown
        layers = {}
        for pipeline in config.pipelines:
            if pipeline.medallion:
                layer = pipeline.medallion.layer.value
                if layer not in layers:
                    layers[layer] = []
                layers[layer].append(pipeline.name)

        if layers:
            click.echo("\nMedallion Layers:")
            for layer in ["bronze", "silver", "gold", "custom"]:
                if layer in layers:
                    click.echo(f"  {layer.upper()}: {', '.join(layers[layer])}")

    except Exception as e:
        click.echo(f"✗ Validation failed: {e}", err=True)
        sys.exit(1)
