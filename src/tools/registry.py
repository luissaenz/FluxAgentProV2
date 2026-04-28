"""ToolRegistry — Centralised registry for CrewAI tools with metadata.

Mirrors the FlowRegistry pattern but also carries operational metadata
(timeout, retry, tags) that the orchestrator can introspect at runtime.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

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

    def get(self, name: str, org_id: str | None = None) -> Type:
        """Get a tool by name. Order: tenant-scoped memory -> global memory -> filesystem fallback."""
        key = name.lower()
        
        # 1. Check tenant-scoped memory first (if org_id provided)
        if org_id:
            scoped_key = f"{org_id}:{key}"
            if scoped_key in self._tools:
                return self._tools[scoped_key]
        
        # 2. Check global memory registry
        if key in self._tools:
            return self._tools[key]
            
        # 3. Fallback to filesystem (src/tools/demo/*.py)
        try:
            tool_class = self._load_from_filesystem(key)
            if tool_class:
                return tool_class
        except Exception as e:
            logger.debug("Failed filesystem fallback for tool '%s': %s", name, e)

        raise ValueError(
            f"Tool '{name}' not found. Available in memory: {list(self._tools.keys())}"
        )

    def _load_from_filesystem(self, name: str) -> Optional[Type]:
        """Try to dynamically import a tool from src.tools.demo."""
        import importlib
        
        # Normalize name (strip prefix and _tool suffix if present)
        # SUPUESTO: Filesystem tools are always global/demo
        clean_name = name.split(":")[-1].replace("_tool", "")
        
        module_paths = [
            f"src.tools.demo.{clean_name}",
            f"src.tools.demo.{clean_name}_tool"
        ]
        
        for module_path in module_paths:
            try:
                module = importlib.import_module(module_path)
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type):
                        if "Tool" in attr_name and not attr_name.startswith("Base"):
                            # Register it in memory for next time as global
                            self.register(name=name)(attr)
                            return attr
            except ImportError:
                continue
                
        return None

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
