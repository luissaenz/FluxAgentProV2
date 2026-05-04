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
    def _parse_mcp_prefix(tool_name: str) -> tuple[str, str] | None:
        """Parse mcp:server:tool format. Returns (server, tool_name) or None."""
        if not tool_name.startswith("mcp:"):
            return None
        parts = tool_name.split(":", 2)
        if len(parts) != 3 or not parts[1] or not parts[2]:
            return None
        return parts[1], parts[2]

    @staticmethod
    def resolve_tools(
        allowed_tools: list[str], org_id: str, *, async_mode: bool = False
    ) -> list:
        """Resolve tool names to instantiated tool objects.

        Central resolution point for both regular and MCP tools.

        Args:
            allowed_tools: List of tool names (may include mcp:server:tool).
            org_id: Organization ID for tenant-scoped resolution.
            async_mode: If True, resolve MCP tools; if False, skip them with warning.

        Returns:
            List of instantiated tool objects.
        """
        tools = []
        for tool_name in allowed_tools:
            if tool_name.startswith("mcp:"):
                mcp_parts = AgentFactory._parse_mcp_prefix(tool_name)
                if not mcp_parts:
                    logger.warning(
                        "Malformed MCP tool prefix '%s', skipping", tool_name
                    )
                    continue

                if not async_mode:
                    logger.warning(
                        "MCP tool '%s' skipped in sync mode (use run_async for MCP support)",
                        tool_name,
                    )
                    continue

                logger.warning(
                    "resolve_tools(async_mode=True) is deprecated. "
                    "Use resolve_tools_async() instead."
                )
                server, mcp_tool_name = mcp_parts
                try:
                    mcp_tool = AgentFactory._resolve_mcp_tool(
                        org_id, server, mcp_tool_name
                    )
                    if mcp_tool:
                        tools.append(mcp_tool)
                except Exception as e:
                    logger.error("Failed to resolve MCP tool '%s': %s", tool_name, e)
            else:
                try:
                    tool_cls = tool_registry.get(tool_name, org_id=org_id)
                    tools.append(tool_cls(org_id=org_id))
                except ValueError:
                    logger.warning(
                        "Tool '%s' not found in registry for agent creation", tool_name
                    )

        return tools

    @staticmethod
    def _resolve_mcp_tool(
        org_id: str, server: str, tool_name: str
    ) -> Any | None:
        """Resolve a single MCP tool from a named server.

        Lazy imports crewai-tools to handle optional dependency.
        """
        import importlib.util

        def _find_spec_safe(name: str):
            try:
                return importlib.util.find_spec(name)
            except (ValueError, ImportError):
                return None

        if _find_spec_safe("crewai_tools") is None:
            raise ImportError(
                "crewai-tools not installed. Install with: pip install fluxagentpro-v2[crew]"
            )
        if _find_spec_safe("mcp") is None:
            raise ImportError(
                "mcp package not installed. Install with: pip install fluxagentpro-v2[crew]"
            )

        from src.tools.mcp_pool import MCPPool

        pool = MCPPool.get()
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            all_tools = asyncio.run_coroutine_threadsafe(
                pool.get_tools(org_id, server), loop
            ).result()
        else:
            all_tools = asyncio.run(pool.get_tools(org_id, server))

        for tool in all_tools:
            if hasattr(tool, "name") and tool.name == tool_name:
                return tool

        logger.warning(
            "MCP tool '%s' not found in server '%s' (available: %s)",
            tool_name,
            server,
            [getattr(t, "name", str(t)) for t in all_tools],
        )
        return None

    @staticmethod
    async def _resolve_mcp_tool_async(
        org_id: str, server: str, tool_name: str
    ) -> Any | None:
        """Async MCP tool resolution — uses await, safe from async context.

        Lazy imports crewai-tools to handle optional dependency.
        """
        import importlib.util

        def _find_spec_safe(name: str):
            try:
                return importlib.util.find_spec(name)
            except (ValueError, ImportError):
                return None

        if _find_spec_safe("crewai_tools") is None:
            raise ImportError(
                "crewai-tools not installed. Install with: pip install fluxagentpro-v2[crew]"
            )
        if _find_spec_safe("mcp") is None:
            raise ImportError(
                "mcp package not installed. Install with: pip install fluxagentpro-v2[crew]"
            )

        from src.tools.mcp_pool import MCPPool

        pool = MCPPool.get()
        try:
            all_tools = await pool.get_tools(org_id, server)
        except Exception as e:
            logger.error(
                "Failed to resolve MCP tool '%s' from server '%s': %s",
                tool_name,
                server,
                e,
            )
            return None

        for tool in all_tools:
            if hasattr(tool, "name") and tool.name == tool_name:
                return tool

        logger.warning(
            "MCP tool '%s' not found in server '%s' (available: %s)",
            tool_name,
            server,
            [getattr(t, "name", str(t)) for t in all_tools],
        )
        return None

    @staticmethod
    async def resolve_tools_async(
        allowed_tools: list[str], org_id: str
    ) -> list:
        """Async variant: resolve regular + MCP tools with await, no deadlock.

        Args:
            allowed_tools: List of tool names (may include mcp:server:tool).
            org_id: Organization ID for tenant-scoped resolution.

        Returns:
            List of instantiated tool objects.
        """
        tools = []
        for tool_name in allowed_tools:
            if tool_name.startswith("mcp:"):
                mcp_parts = AgentFactory._parse_mcp_prefix(tool_name)
                if not mcp_parts:
                    logger.warning(
                        "Malformed MCP tool prefix '%s', skipping", tool_name
                    )
                    continue

                server, mcp_tool_name = mcp_parts
                try:
                    mcp_tool = await AgentFactory._resolve_mcp_tool_async(
                        org_id, server, mcp_tool_name
                    )
                    if mcp_tool:
                        tools.append(mcp_tool)
                except Exception as e:
                    logger.error("Failed to resolve MCP tool '%s': %s", tool_name, e)
            else:
                try:
                    tool_cls = tool_registry.get(tool_name, org_id=org_id)
                    tools.append(tool_cls(org_id=org_id))
                except ValueError:
                    logger.warning(
                        "Tool '%s' not found in registry for agent creation", tool_name
                    )

        return tools

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

        allowed_tools = config.get("allowed_tools", [])
        tools = AgentFactory.resolve_tools(allowed_tools, org_id)

        return Agent(
            role=soul.get("role") or config.get("role") or "Specialised Agent",
            goal=soul.get("goal", "Complete the assigned task."),
            backstory=soul.get("backstory", "You are a highly efficient AI agent."),
            verbose=False,
            allow_delegation=False,
            llm=llm,
            max_iter=config.get("max_iter", 5),
            tools=tools,
        )

    @staticmethod
    async def create_agent_async(config: Dict[str, Any], org_id: str) -> Agent:
        """Create a CrewAI Agent with full async MCP tool resolution.

        Use this in run_async() paths to enable MCP tools without deadlock.
        """
        soul = config.get("soul_json", {})
        settings = get_settings()
        llm = settings.get_llm()

        allowed_tools = config.get("allowed_tools", [])
        tools = await AgentFactory.resolve_tools_async(allowed_tools, org_id)

        return Agent(
            role=soul.get("role") or config.get("role") or "Specialised Agent",
            goal=soul.get("goal", "Complete the assigned task."),
            backstory=soul.get("backstory", "You are a highly efficient AI agent."),
            verbose=False,
            allow_delegation=False,
            llm=llm,
            max_iter=config.get("max_iter", 5),
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
