"""FlowRegistry — Centralised registry for Flow classes.

Flows self-register at import time via the ``@register_flow`` decorator,
keeping the API Gateway completely decoupled from concrete implementations.
"""

from __future__ import annotations

from typing import Type, Dict, Callable, Any
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
    """Thread-safe (GIL) registry mapping lowercase names → Flow classes."""

    def __init__(self) -> None:
        self._flows: Dict[str, Type] = {}
        self._builders: Dict[str, Callable[[], Any]] = {}

    # ── registration ────────────────────────────────────────────

    def register(self, name: str | None = None) -> Callable[[Type], Type]:
        """
        Class decorator that registers a Flow.

        Usage::

            @flow_registry.register("my_flow")
            class MyFlow(BaseFlow): ...
        """

        def decorator(flow_class: Type) -> Type:
            flow_name = (name or flow_class.__name__).lower()
            self._flows[flow_name] = flow_class
            logger.info("Registered flow: %s", flow_name)
            return flow_class

        return decorator

    def register_builder(self, name: str, builder: Callable[[], Any]) -> None:
        """Register a lazy builder function."""
        self._builders[name.lower()] = builder

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
def register_flow(name: str | None = None) -> Callable[[Type], Type]:
    """Shortcut for ``flow_registry.register(name)``."""
    return flow_registry.register(name)
