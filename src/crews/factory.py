"""src/crews/factory.py — Factory for instantiating CrewAI objects from JSON definitions."""

import logging
from typing import Any, Dict

from crewai import Agent, Task

from src.config import get_settings
from src.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory to reconstruct CrewAI agents and tasks from JSON definitions."""

    @staticmethod
    def create_agent(config: Dict[str, Any], org_id: str) -> Agent:
        """Create a CrewAI Agent from an agent_catalog record or bundle manifest.

        Args:
            config: Agent configuration (must contain 'soul_json')
            org_id: Organization ID for tool resolution
        """
        soul = config.get("soul_json", {})
        settings = get_settings()
        llm = settings.get_llm()

        # Resolve tools
        allowed_tools = config.get("allowed_tools", [])
        tools = []
        for tool_name in allowed_tools:
            try:
                tool_cls = tool_registry.get(tool_name, org_id=org_id)
                tools.append(tool_cls(org_id=org_id))
            except ValueError:
                logger.warning(
                    "Tool '%s' not found in registry for agent creation", tool_name
                )

        return Agent(
            role=soul.get("role") or config.get("role") or "Specialised Agent",
            goal=soul.get("goal", "Complete the assigned task."),
            backstory=soul.get("backstory", "You are a highly efficient AI agent."),
            verbose=False,
            allow_delegation=False,  # Rule R2
            llm=llm,
            max_iter=config.get("max_iter", 5),  # Rule R8
            tools=tools,
        )

    @staticmethod
    def create_task(
        description: str, agent: Agent, expected_output: str = "Structured result"
    ) -> Task:
        """Create a CrewAI Task."""
        return Task(
            description=description, agent=agent, expected_output=expected_output
        )
