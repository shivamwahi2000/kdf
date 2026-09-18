"""Bootstrap KDF registries with default connectors and skills."""

from kdf.core.registry import connector_registry, skill_registry
from kdf.connectors.postgres.connector import PostgresConnector
from kdf.connectors.s3.connector import S3Connector
from kdf.connectors.delta.connector import DeltaConnector
from kdf.connectors.kafka.connector import KafkaConnector
from kdf.skills.ingestion.full_load import FullLoadSkill
from kdf.skills.ingestion.incremental import IncrementalLoadSkill
from kdf.skills.transformation.deduplicate import DeduplicateSkill
from kdf.skills.aggregation.aggregate import AggregateSkill
from kdf.skills.quality.not_null import NotNullSkill
from kdf.skills.quality.unique import UniqueSkill
from kdf.skills.quality.freshness import FreshnessSkill
from kdf.skills.schema.evolution import SchemaEvolutionSkill
from kdf.skills.reconciliation.reconcile import ReconciliationSkill


def bootstrap_registries():
    """Register all built-in connectors and skills."""

    # Register connectors
    connector_registry.register_connector("postgres", PostgresConnector)
    connector_registry.register_connector("s3", S3Connector)
    connector_registry.register_connector("delta", DeltaConnector)
    connector_registry.register_connector("kafka", KafkaConnector)

    # Register ingestion skills
    skill_registry.register_skill("full_load", FullLoadSkill)
    skill_registry.register_skill("incremental", IncrementalLoadSkill)

    # Register transformation skills
    skill_registry.register_skill("deduplicate", DeduplicateSkill)
    skill_registry.register_skill("aggregate", AggregateSkill)

    # Register quality skills
    skill_registry.register_skill("not_null", NotNullSkill)
    skill_registry.register_skill("unique", UniqueSkill)
    skill_registry.register_skill("freshness", FreshnessSkill)

    # Register schema skills
    skill_registry.register_skill("schema_evolution", SchemaEvolutionSkill)

    # Register reconciliation skills
    skill_registry.register_skill("reconcile", ReconciliationSkill)


# Auto-bootstrap on import
bootstrap_registries()
