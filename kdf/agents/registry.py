"""Agent skill registry."""

from typing import Dict, List
import os


class AgentSkillRegistry:
    """Registry for agent skills."""

    def __init__(self, skills_path: str = "./kdf/agents/skills"):
        """Initialize registry.

        Args:
            skills_path: Base path for agent skills
        """
        self.skills_path = skills_path
        self._skills: Dict[str, str] = {}

    def register(self, name: str, path: str) -> None:
        """Register an agent skill.

        Args:
            name: Skill name
            path: Path to skill directory
        """
        self._skills[name] = path

    def get(self, name: str) -> str:
        """Get agent skill path.

        Args:
            name: Skill name

        Returns:
            Path to skill directory
        """
        return self._skills.get(name)

    def list(self) -> List[str]:
        """List all registered agent skills."""
        return list(self._skills.keys())

    def discover(self) -> None:
        """Auto-discover agent skills from skills directory."""
        if not os.path.exists(self.skills_path):
            return

        for item in os.listdir(self.skills_path):
            skill_path = os.path.join(self.skills_path, item)
            if os.path.isdir(skill_path):
                # Check if SKILL.md exists
                skill_file = os.path.join(skill_path, "SKILL.md")
                if os.path.exists(skill_file):
                    self.register(item, skill_path)
