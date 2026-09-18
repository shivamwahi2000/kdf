"""Base agent skill interface."""

from abc import ABC
from typing import Dict, List
from pydantic import BaseModel

from kdf.core.models import AgentPermissions


class AgentSkillManifest(BaseModel):
    """Agent skill manifest."""

    name: str
    version: str
    type: str = "agent-skill"
    description: str
    requires: Dict[str, str]
    tools: List[str]
    permissions: AgentPermissions


class AgentSkill(ABC):
    """Base class for agent skills."""

    def __init__(self, manifest_path: str):
        """Initialize agent skill.

        Args:
            manifest_path: Path to skill manifest
        """
        self.manifest_path = manifest_path
        # In future versions, load and parse manifest
