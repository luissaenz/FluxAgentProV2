"""ToolRegistry — Centralised registry for CrewAI tools with metadata.

Mirrors the FlowRegistry pattern but also carries operational metadata
(timeout, retry, tags) that the orchestrator can introspect at runtime.
"""

from __future__ import annotations

from typing import Type, Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ToolMetadata:
    """Operational metadata attached to every registered tool."""

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    timeout_seconds: int = 30
    retry_count: int = 3
    tags: List[str] = field(default_factory=list)


class ToolRegistry:
    """Registry mapping lowercase tool names → classes + metadata."""

    def __init__(self) -> None:
        self._tools: Dict[str, Type] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._instances: Dict[str, Any] = {}

    # ── registration ────────────────────────────────────────────

    def register(
        self,
        name: str | None = None,
        description: str = "",
        requires_approval: bool = False,
        timeout_seconds: int = 30,
        retry_count: int = 3,
        tags: List[str] | None = None,
    ) -> Callable[[Type], Type]:
        """
        Decorator to register a Tool with metadata.

        Usage::

            @tool_registry.register("fetch_url", description="Fetch URL content")
            class FetchURLTool(BaseTool): ...
        """

        def decorator(tool_class: Type) -> Type:
            tool_name = (name or tool_class.__name__).lower()
            self._tools[tool_name] = tool_class
            self._metadata[tool_name] = ToolMetadata(
                name=tool_name,
                description=description,
                requires_approval=requires_approval,
                timeout_seconds=timeout_seconds,
                retry_count=retry_count,
                tags=tags or [],
            )
            logger.info("Registered tool: %s", tool_name)
            return tool_class

        return decorator

    # ── lookup ──────────────────────────────────────────────────

    def get(self, name: str) -> Type:
        key = name.lower()
        if key not in self._tools:
            raise ValueError(
                f"Tool '{name}' not found. Available: {list(self._tools.keys())}"
            )
        return self._tools[key]

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        return self._metadata.get(name.lower())

    def get_or_create(self, name: str, **kwargs: Any) -> Any:
        """Singleton accessor — create on first access."""
        key = name.lower()
        if key not in self._instances:
            self._instances[key] = self.get(name)(**kwargs)
        return self._instances[key]

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def list_by_tag(self, tag: str) -> List[str]:
        return [n for n, m in self._metadata.items() if tag in m.tags]

    def clear(self) -> None:
        self._tools.clear()
        self._metadata.clear()
        self._instances.clear()


# ── global singleton ────────────────────────────────────────────
tool_registry = ToolRegistry()


# ── convenience decorator ───────────────────────────────────────
def register_tool(
    name: str | None = None,
    description: str = "",
    requires_approval: bool = False,
    timeout_seconds: int = 30,
    retry_count: int = 3,
    tags: List[str] | None = None,
) -> Callable[[Type], Type]:
    """Shortcut for ``tool_registry.register(…)``."""
    return tool_registry.register(
        name, description, requires_approval, timeout_seconds, retry_count, tags
    )
