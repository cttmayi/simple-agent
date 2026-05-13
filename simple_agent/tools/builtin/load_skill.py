
"""Load a skill dynamically."""

from typing import Dict, Any
from simple_agent.tools.registry import get_global_registry, ToolDefinition
from simple_agent.core.events import Event


class LoadSkill:
    """Load a skill's full instructions."""

    name = "load_skill"
    description = "Load a skill's full instructions by name"

    # This will be set by Runtime
    _skill_loader = None
    _loaded_skills = None
    _runtime = None  # Store runtime reference for logging
    _event_bus = None  # Event bus for publishing events

    @classmethod
    def set_runtime(cls, skill_loader, loaded_skills, runtime=None, event_bus=None):
        """Set runtime dependencies."""
        cls._skill_loader = skill_loader
        cls._loaded_skills = loaded_skills
        cls._runtime = runtime
        cls._event_bus = event_bus

    @staticmethod
    def execute(skill_name: str) -> Dict[str, Any]:
        """Load a skill's full content.

        Args:
            skill_name: Name of the skill to load

        Returns:
            Dict with success and message
        """
        if LoadSkill._skill_loader is None:
            return {
                "success": False,
                "message": "Skill loader not initialized"
            }

        if skill_name in LoadSkill._loaded_skills:
            return {
                "success": True,
                "message": f"Skill '{skill_name}' is already loaded.",
            }

        content = LoadSkill._skill_loader.get_skill_content(skill_name)

        if content:
            LoadSkill._loaded_skills.add(skill_name)
            # Log skill loaded
            if LoadSkill._runtime:
                LoadSkill._runtime._logger.log_skill_loaded(skill_name)

            # Publish skill_loaded event
            if LoadSkill._event_bus:
                LoadSkill._event_bus.publish(Event("skill_loaded", {
                    "skill_name": skill_name
                }))

            return {
                "success": True,
                "message": f"Loaded skill: {skill_name}",
                "content": content,  # Return the actual skill content
                "debug": f"Content length: {len(content)} chars"  # Debug info
            }

        return {
            "success": False,
            "message": f"Skill '{skill_name}' not found",
            "debug": "No content found"
        }


# Register with ToolRegistry
load_skill_tool_def = ToolDefinition(
    name=LoadSkill.name,
    description=LoadSkill.description,
    fn=LoadSkill.execute,
    parameters={
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "Name of the skill to load"
            }
        },
        "required": ["skill_name"]
    }
)
