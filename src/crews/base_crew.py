"""BaseCrew — Loads agent definition from agent_catalog and runs a single-agent crew.

Phase 3: Used by multi-crew flows to instantiate specialised agents per role.
Each agent's personality (soul_json), allowed tools, and constraints come from DB.

Rule R1: Flow is orchestrator, agents are executors only.
Rule R2: allow_delegation=False always.
Rule R8: max_iter explicit (≤5 for production).
"""

from __future__ import annotations

from typing import Dict, Any, Optional, List
import logging

from ..db.session import get_service_client
from ..config import get_settings
from ..tools.registry import tool_registry

logger = logging.getLogger(__name__)


class CrewConfigError(Exception):
    """Raised when agent_catalog has no matching entry."""


class BaseCrew:
    """Load an agent from agent_catalog by (org_id, role) and run a single-agent crew.

    Usage::

        crew = BaseCrew(org_id, role="analyst")
        result = crew.run(
            task_description="Analyse the data.",
            inputs={"data": {...}},
        )
    """

    def __init__(self, org_id: str, role: str) -> None:
        self.org_id = org_id
        self.role = role
        self._agent_config: Optional[Dict[str, Any]] = None

    def _load_agent_config(self) -> Dict[str, Any]:
        """Fetch agent definition from agent_catalog."""
        if self._agent_config is not None:
            return self._agent_config

        svc = get_service_client()
        result = (
            svc.table("agent_catalog")
            .select("*")
            .eq("org_id", self.org_id)
            .eq("role", self.role)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )

        if not result.data:
            raise CrewConfigError(
                f"No active agent with role '{self.role}' for org '{self.org_id}'"
            )

        self._agent_config = result.data
        return self._agent_config

    def _resolve_tools(self, allowed_tools: List[str]) -> list:
        """Resolve tool names to instantiated tool objects."""
        tools = []
        for tool_name in allowed_tools:
            try:
                tool_cls = tool_registry.get(tool_name)
                tools.append(tool_cls(org_id=self.org_id))
            except ValueError:
                logger.warning("Tool '%s' not found in registry", tool_name)
        return tools

    def run(
        self,
        task_description: str,
        inputs: Optional[Dict[str, Any]] = None,
        expected_output: str = "Structured result of the analysis.",
    ) -> Any:
        """Build and execute the crew synchronously.

        Args:
            task_description: What the agent should do.
            inputs: Variables interpolated into the task description.
            expected_output: Description of expected output format.

        Returns:
            CrewOutput from crew.kickoff().
        """
        from crewai import Agent, Crew, Process, Task

        config = self._load_agent_config()
        soul = config.get("soul_json", {})
        settings = get_settings()
        llm = settings.get_llm()

        # Resolve tools from allowed_tools list
        allowed_tools = config.get("allowed_tools", [])
        tools = self._resolve_tools(allowed_tools)

        agent = Agent(
            role=soul.get("role", self.role),
            goal=soul.get("goal", "Complete the assigned task."),
            backstory=soul.get("backstory", "You are a specialised agent."),
            verbose=False,
            allow_delegation=False,  # Rule R2
            llm=llm,
            max_iter=config.get("max_iter", 5),  # Rule R8
            tools=tools,
        )

        task = Task(
            description=task_description,
            expected_output=expected_output,
            agent=agent,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )

        return crew.kickoff(inputs=inputs or {})

    async def run_async(
        self,
        task_description: str,
        inputs: Optional[Dict[str, Any]] = None,
        expected_output: str = "Structured result of the analysis.",
    ) -> Any:
        """Build and execute the crew asynchronously.

        Use this in async Flows to avoid blocking the event loop.
        """
        from crewai import Agent, Crew, Process, Task

        config = self._load_agent_config()
        soul = config.get("soul_json", {})
        settings = get_settings()
        llm = settings.get_llm()

        allowed_tools = config.get("allowed_tools", [])
        tools = self._resolve_tools(allowed_tools)

        agent = Agent(
            role=soul.get("role", self.role),
            goal=soul.get("goal", "Complete the assigned task."),
            backstory=soul.get("backstory", "You are a specialised agent."),
            verbose=False,
            allow_delegation=False,
            llm=llm,
            max_iter=config.get("max_iter", 5),
            tools=tools,
        )

        task = Task(
            description=task_description,
            expected_output=expected_output,
            agent=agent,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )

        return await crew.kickoff_async(inputs=inputs or {})

    async def kickoff_async(self, inputs: Optional[Dict[str, Any]] = None) -> Any:
        """Alias for run_async() — compatibility with Phase 3 documentation."""
        return await self.run_async(
            task_description="Ejecutar tarea asignada",
            inputs=inputs or {},
        )
