"""Ingestion skills."""

from kdf.skills.ingestion.full_load import FullLoadSkill
from kdf.skills.ingestion.incremental import IncrementalLoadSkill

__all__ = ["FullLoadSkill", "IncrementalLoadSkill"]
