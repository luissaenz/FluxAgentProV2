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
        """Get a tool by name. Order: tenant-scoped memory -> global memory -> DB lookup -> filesystem fallback."""
        key = name.lower()

        # 1. Check tenant-scoped memory first (if org_id provided)
        if org_id:
            scoped_key = f"{org_id}:{key}"
            if scoped_key in self._tools:
                return self._tools[scoped_key]

        # 2. Check global memory registry
        if key in self._tools:
            return self._tools[key]

        # 3. DB Lookup (skill_catalog)
        if org_id:
            try:
                tool_class = self._load_from_db(key, org_id)
                if tool_class:
                    return tool_class
            except Exception as e:
                logger.debug(
                    "Failed DB lookup for tool '%s' in org '%s': %s", name, org_id, e
                )

        # 4. Fallback to filesystem (src/tools/demo/*.py) (Gated by Strict Mode)
        from src.config import get_settings

        if get_settings().fap_strict_mode:
            logger.info(
                "Strict mode active: Skipping filesystem fallback for tool '%s'", name
            )
            raise ValueError(
                f"Tool '{name}' not found. Strict mode active, filesystem fallback disabled."
            )

        try:
            tool_class = self._load_from_filesystem(key)
            if tool_class:
                return tool_class
        except Exception as e:
            logger.debug("Failed filesystem fallback for tool '%s': %s", name, e)

        raise ValueError(
            f"Tool '{name}' not found. Available in memory: {list(self._tools.keys())}"
        )

    def _load_from_db(self, name: str, org_id: str) -> Optional[Type]:
        """Fetch skill from DB, validate safety, compile and register in memory."""
        from RestrictedPython import compile_restricted

        from src.db.session import get_tenant_client
        from src.services.security_guard import SecurityGuard

        try:
            with get_tenant_client(org_id) as db:
                result = (
                    db.table("skill_catalog")
                    .select("code_source")
                    .eq("org_id", org_id)
                    .eq("name", name)
                    .maybe_single()
                    .execute()
                )

                if not (result and result.data):
                    return None

                code_source = result.data["code_source"]
                filename = f"<db_skill_{org_id}_{name}>"

                # 1. Security Scan (AST + Compilation check)
                guard = SecurityGuard()
                guard.validate_skill(code_source, filename)  # Raises SecurityError if unsafe

                # 2. Restricted Compilation
                # Note: We use 'exec' mode. The code must define a class that we can extract.
                byte_code = compile_restricted(code_source, filename, "exec")

                # 3. Execution in restricted namespace
                # We provide a safe built-in environment
                from RestrictedPython import safe_builtins

                loc: Dict[str, Any] = {}
                # SUPUESTO: Las skills de DB deben seguir el patrón de las de disco:
                # Deben definir una clase que herede de BaseTool o similar.
                exec(byte_code, {"__builtins__": safe_builtins}, loc)

                # 4. Extract Tool class
                for attr in loc.values():
                    if (
                        isinstance(attr, type)
                        and "Tool" in attr.__name__
                        and not attr.__name__.startswith("Base")
                    ):
                        # Register in memory (tenant-scoped)
                        self.register(name=f"{org_id}:{name}")(attr)
                        logger.info(
                            "Successfully loaded skill '%s' from DB for org '%s'",
                            name,
                            org_id,
                        )
                        return attr

                logger.warning(
                    "DB Skill '%s' for org '%s' found but no Tool class detected in source.",
                    name,
                    org_id,
                )
                return None

        except Exception as exc:
            logger.error("Error loading skill '%s' from DB: %s", name, exc)
            return None

    def _load_from_filesystem(self, name: str) -> Optional[Type]:
        """Try to dynamically import a tool from src.tools.demo."""
        import importlib

        # Normalize name (strip prefix and _tool suffix if present)
        # SUPUESTO: Filesystem tools are always global/demo
        clean_name = name.split(":")[-1].replace("_tool", "")

        module_paths = [
            f"src.tools.demo.{clean_name}",
            f"src.tools.demo.{clean_name}_tool",
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

    def get_or_create(self, name: str, org_id: str | None = None, **kwargs: Any) -> Any:
        """Singleton accessor — create on first access."""
        key = name.lower()
        if key not in self._instances:
            self._instances[key] = self.get(name, org_id=org_id)(**kwargs)
        return self._instances[key]

    def list_tools(self) -> List[str]:
        return list(self._tools.keys())

    def list_by_tag(self, tag: str) -> List[str]:
        return [n for n, m in self._metadata.items() if tag in m.tags]

    def clear(self) -> None:
        self._tools.clear()
        self._metadata.clear()
        self._instances.clear()

    def invalidate_tenant_cache(self, org_id: str) -> None:
        """Clear all tools and instances cached for a specific tenant.

        This enables 'Hot-Reload' by forcing the registry to reload skills
        from the database or re-register them from a new bundle.
        """
        prefix = f"{org_id}:"

        # 1. Remove tools
        keys_to_remove = [k for k in self._tools.keys() if k.startswith(prefix)]
        for k in keys_to_remove:
            self._tools.pop(k, None)
            self._metadata.pop(k, None)
            logger.debug("Removed cached tool from memory: %s", k)

        # 2. Remove instances (Singletons)
        # SUPUESTO: Instances might have been created with scoped or unscoped names.
        # We also clear instances whose name starts with the prefix.
        instance_keys = [k for k in self._instances.keys() if k.startswith(prefix)]
        for k in instance_keys:
            self._instances.pop(k, None)
            logger.debug("Invalidated tool instance: %s", k)

        logger.info("Invalidated cache for tenant: %s", org_id)

    def refresh_tenant(self, org_id: str) -> None:
        """Alias for invalidate_tenant_cache to match Roadmap terminology."""
        self.invalidate_tenant_cache(org_id)


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
