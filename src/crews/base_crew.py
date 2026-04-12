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
        query = (
            svc.table("agent_catalog")
            .select("*")
            .eq("org_id", self.org_id)
            .eq("role", self.role)
            .eq("is_active", True)
            .maybe_single()
        )
        result = query.execute()

        if result is None:
            logger.error(
                "Supabase query returned None for role '%s' in org '%s'. Check connectivity or client config.",
                self.role, self.org_id
            )
            raise CrewConfigError(f"Database unavailable or returned empty for role '{self.role}'")

        if not result.data:
            raise CrewConfigError(
                f"No active agent with role '{self.role}' for org '{self.org_id}' (Checked table 'agent_catalog')"
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
            CrewOutput from crew.kickoff() with token usage attached.
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

        result = crew.kickoff(inputs=inputs or {})

        # Extract token usage from crew result
        self._extract_token_usage(result)

        return result

    def _extract_token_usage(self, result: Any) -> None:
        """Extract and store token usage from CrewAI result."""
        tokens = 0

        # Try token_usage attribute (CrewAI standard)
        if hasattr(result, "token_usage") and result.token_usage:
            token_data = result.token_usage
            if hasattr(token_data, "total_tokens"):
                tokens = token_data.total_tokens
            elif isinstance(token_data, dict):
                tokens = token_data.get("total_tokens", 0)

        # Try usage_metrics attribute
        elif hasattr(result, "usage_metrics") and result.usage_metrics:
            metrics = result.usage_metrics
            if hasattr(metrics, "total_tokens"):
                tokens = metrics.total_tokens
            elif isinstance(metrics, dict):
                tokens = metrics.get("total_tokens", 0)

        # Try tokens attribute
        elif hasattr(result, "tokens") and result.tokens:
            tokens = result.tokens

        # Try to get from crew.usage_metrics (alternative path)
        elif hasattr(result, "crew") and hasattr(result.crew, "usage_metrics"):
            crew_metrics = result.crew.usage_metrics
            if hasattr(crew_metrics, "total_tokens"):
                tokens = crew_metrics.total_tokens

        # Store in instance for retrieval after run
        self._last_tokens_used = tokens

    def get_last_tokens_used(self) -> int:
        """Return tokens consumed in last run."""
        return getattr(self, "_last_tokens_used", 0)

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

        result = await crew.kickoff_async(inputs=inputs or {})

        # Extract token usage from crew result
        self._extract_token_usage(result)

        return result

    async def kickoff_async(self, inputs: Optional[Dict[str, Any]] = None) -> Any:
        """Alias for run_async() — compatibility with Phase 3 documentation."""
        return await self.run_async(
            task_description="Ejecutar tarea asignada",
            inputs=inputs or {},
        )
