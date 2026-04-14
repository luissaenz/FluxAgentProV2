"""FlowRegistry — Centralised registry for Flow classes.

Flows self-register at import time via the ``@register_flow`` decorator,
keeping the API Gateway completely decoupled from concrete implementations.

Phase 4: Added ``depends_on`` and ``category`` metadata to model business
process hierarchies (e.g. "Venta" → "Facturación").
"""

from __future__ import annotations

from typing import Type, Dict, Callable, Any, Optional, List
import logging
import re

logger = logging.getLogger(__name__)


def _normalize_flow_name(name: str) -> str:
    """Convert PascalCase or other formats to snake_case for registry lookup.

    Examples:
        "CotizacionFlow" → "cot izacion_flow"
        "cotizacion_flow" → "cotizacion_flow"
        "ComprasFlow" → "compras_flow"
    """
    # Convert CamelCase to snake_case
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class FlowRegistry:
    """Thread-safe (GIL) registry mapping lowercase names → Flow classes.

    Phase 4: Each flow entry now stores optional metadata:
    - depends_on: list of flow names that must complete before this flow
    - category: business process category (e.g. "ventas", "facturacion")
    """

    def __init__(self) -> None:
        self._flows: Dict[str, Type] = {}
        self._builders: Dict[str, Callable[[], Any]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    # ── registration ────────────────────────────────────────────

    def register(
        self,
        name: str | None = None,
        *,
        depends_on: Optional[List[str]] = None,
        category: Optional[str] = None,
        description: str = "",
    ) -> Callable[[Type], Type]:
        """
        Class decorator that registers a Flow.

        Usage::

            @flow_registry.register("my_flow", category="ventas")
            class MyFlow(BaseFlow): ...

            @flow_registry.register(
                "facturacion_flow",
                depends_on=["venta_flow"],
                category="facturacion",
                description="Procesa facturación post-venta",
            )
            class FacturacionFlow(BaseFlow): ...
        """

        def decorator(flow_class: Type) -> Type:
            flow_name = (name or flow_class.__name__).lower()
            self._flows[flow_name] = flow_class

            # Store metadata
            self._metadata[flow_name] = {
                "depends_on": depends_on or [],
                "category": category,
                "description": description,
            }

            logger.info(
                "Registered flow: %s (category=%s, depends_on=%s)",
                flow_name,
                category,
                depends_on,
            )
            return flow_class

        return decorator

    def register_builder(self, name: str, builder: Callable[[], Any]) -> None:
        """Register a lazy builder function."""
        self._builders[name.lower()] = builder

    # ── metadata access ─────────────────────────────────────────

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """Return metadata for a flow, or defaults if not found."""
        key = _normalize_flow_name(name)
        return self._metadata.get(key, {"depends_on": [], "category": None})

    def get_hierarchy(self) -> Dict[str, Dict[str, Any]]:
        """Return full hierarchy with metadata for all flows."""
        result = {}
        for flow_name in self._flows:
            meta = self._metadata.get(flow_name, {"depends_on": [], "category": None})
            result[flow_name] = {
                "depends_on": meta.get("depends_on", []),
                "category": meta.get("category"),
            }
        return result

    def get_flows_by_category(self) -> Dict[str, List[str]]:
        """Group flows by their category."""
        groups: Dict[str, List[str]] = {}
        for flow_name, meta in self._metadata.items():
            cat = meta.get("category") or "sin_categoria"
            if cat not in groups:
                groups[cat] = []
            groups[cat].append(flow_name)
        return groups

    # ── validation ──────────────────────────────────────────────

    def validate_dependencies(self) -> Dict[str, List[str]]:
        """Identify flows that reference non-existent dependencies.

        Returns a dict mapping flow_name → list of invalid dependency names.
        Empty dict means all dependencies are valid.
        """
        invalid: Dict[str, List[str]] = {}
        registered_names = set(self._flows.keys())

        for flow_name, meta in self._metadata.items():
            deps = meta.get("depends_on", [])
            missing = [dep for dep in deps if dep.lower() not in registered_names]
            if missing:
                invalid[flow_name] = missing
                logger.warning(
                    "Flow '%s' has invalid dependencies: %s",
                    flow_name,
                    missing,
                )

        return invalid

    def detect_cycles(self) -> List[List[str]]:
        """Detect dependency cycles using DFS (O(V+E)).

        Returns a list of cycles, where each cycle is a list of flow names
        forming the cycle (e.g. [["a", "b", "a"], ["x", "y", "z", "x"]]).
        """
        cycles: List[List[str]] = []
        visited: set = set()
        rec_stack: set = set()
        path: List[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            deps = self._metadata.get(node, {}).get("depends_on", [])
            for dep in deps:
                dep_lower = dep.lower()
                if dep_lower not in self._flows:
                    continue  # skip non-existent deps (handled by validate_dependencies)
                if dep_lower not in visited:
                    dfs(dep_lower)
                elif dep_lower in rec_stack:
                    # Found a cycle — extract it from the path
                    cycle_start = path.index(dep_lower)
                    cycle = path[cycle_start:] + [dep_lower]
                    cycles.append(cycle)

            path.pop()
            rec_stack.discard(node)

        for flow_name in self._flows:
            if flow_name not in visited:
                dfs(flow_name)

        if cycles:
            logger.warning("Detected dependency cycles: %s", cycles)

        return cycles

    def run_full_validation(self) -> Dict[str, Any]:
        """Run complete graph validation and return results.

        Designed to be called once after all flows are registered (post-startup).
        Returns a validation report suitable for API responses.
        """
        invalid_deps = self.validate_dependencies()
        cycles = self.detect_cycles()

        return {
            "invalid_dependencies": invalid_deps,
            "cycles": cycles,
        }

    # ── lookup ──────────────────────────────────────────────────

    def get(self, name: str) -> Type:
        """Return the Flow class for *name*, or raise ``ValueError``.

        Supports multiple naming formats:
        - PascalCase: "CotizacionFlow" → looks up "cotizacion_flow"
        - snake_case: "cotizacion_flow" → looks up "cotizacion_flow"
        - lowercase: "cot izacionflow" → looks up "cot izacionflow"
        """
        key = _normalize_flow_name(name)
        if key not in self._flows:
            raise ValueError(
                f"Flow '{name}' not found. Available: {list(self._flows.keys())}"
            )
        return self._flows[key]

    def create(self, name: str, **kwargs: Any) -> Any:
        """Instantiate a registered Flow by name."""
        return self.get(name)(**kwargs)

    def has(self, name: str) -> bool:
        """Check whether *name* has been registered."""
        return name.lower() in self._flows

    def list_flows(self) -> list[str]:
        """Return all registered flow names."""
        return list(self._flows.keys())

    def clear(self) -> None:
        """Clear the registry (useful in tests)."""
        self._flows.clear()
        self._builders.clear()


# ── global singleton ────────────────────────────────────────────
flow_registry = FlowRegistry()


# ── convenience decorator ───────────────────────────────────────
def register_flow(
    name: str | None = None,
    *,
    depends_on: Optional[List[str]] = None,
    category: Optional[str] = None,
    description: str = "",
) -> Callable[[Type], Type]:
    """Shortcut for ``flow_registry.register(name)`` with optional metadata."""
    return flow_registry.register(
        name, depends_on=depends_on, category=category, description=description
    )
