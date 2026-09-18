"""
KDF — Krianno Data Framework

Build the foundation for an Agentic Data Engineering Ecosystem.
"""

__version__ = "0.1.0"
__author__ = "Krianno TechLabs"

from kdf.core.pipeline import Pipeline
from kdf.core.config import PipelineConfig
from kdf.core.context import ExecutionContext

__all__ = [
    "Pipeline",
    "PipelineConfig",
    "ExecutionContext",
]
