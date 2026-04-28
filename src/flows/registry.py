"""FlowRegistry — Centralised registry for Flow classes.

Flows self-register at import time via the ``@register_flow`` decorator,
keeping the API Gateway completely decoupled from concrete implementations.

Phase 4: Added ``depends_on`` and ``category`` metadata to model business
process hierarchies (e.g. "Venta" → "Facturación").
"""

from __future__ import annotations

import logging
import re
from typing import Any, Callable, Dict, List, Optional, Type

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

            # Guardar el nombre oficial en la clase para que BaseFlow lo use
            flow_class._registered_flow_name = flow_name

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

        status = "error" if (invalid_deps or cycles) else "success"
        return {
            "status": status,
            "invalid_dependencies": invalid_deps,
            "cycles": cycles,
        }

    # ── lookup ──────────────────────────────────────────────────

    def get(self, name: str, org_id: str | None = None) -> Type:
        """Return the Flow class for *name*.
        
        Order: memory -> DB lookup (if org_id provided) -> raise ValueError.
        """
        # 1. Memory lookup
        key = name.lower()
        if key in self._flows:
            return self._flows[key]

        normalized_key = _normalize_flow_name(name)
        if normalized_key in self._flows:
            return self._flows[normalized_key]

        # 2. DB Lookup (workflow_templates)
        if org_id:
            try:
                flow_class = self._load_from_db(key, org_id)
                if flow_class:
                    return flow_class
            except Exception as e:
                logger.debug("Failed DB lookup for flow '%s' in org '%s': %s", name, org_id, e)

        raise ValueError(
            f"Flow '{name}' not found. Available in memory: {list(self._flows.keys())}"
        )

    def _load_from_db(self, flow_type: str, org_id: str) -> Optional[Type]:
        """Fetch workflow template from DB and wrap in DynamicWorkflow."""
        from src.db.session import get_tenant_client
        from src.flows.dynamic_flow import DynamicWorkflow

        try:
            with get_tenant_client(org_id) as db:
                result = (
                    db.table("workflow_templates")
                    .select("definition")
                    .eq("org_id", org_id)
                    .eq("flow_type", flow_type)
                    .eq("is_active", True)
                    .maybe_single()
                    .execute()
                )
                
                if not (result and result.data):
                    return None
                
                definition = result.data["definition"]
                
                # Wrap in DynamicWorkflow
                # SUPUESTO: DynamicWorkflow.register_class retorna una clase configurada
                # que podemos registrar en memoria para el futuro.
                # Nota: Necesitamos importar DynamicWorkflow localmente para evitar circulares.
                
                # Para evitar registrar clases temporales globalmente en _flows 
                # (lo que podría colisionar si diferentes orgs tienen el mismo flow_type),
                # el análisis sugería retornar la clase configurada.
                
                # Creamos una subclase anónima de DynamicWorkflow para esta definición
                class BoundDynamicFlow(DynamicWorkflow):
                    _registered_flow_name = flow_type
                    def __init__(self, **kwargs):
                        # Forzamos la definición en el constructor o via clase
                        super().__init__(**kwargs)
                
                # Inyectamos la definición en la clase para que DynamicWorkflow la use
                BoundDynamicFlow.definition = definition
                
                # Opcional: registrar en memoria para esta sesión/tenant?
                # El análisis dice: "se registra en memoria". 
                # Pero FlowRegistry es global. Si lo registro en _flows[flow_type],
                # la siguiente org que pida ese flow_type recibirá el de la org anterior.
                # ERROR: Debemos usar un prefijo o no registrar en el registry global
                # si es dinámico.
                
                # Sin embargo, el endpoint run_flow usa require_org_id, 
                # por lo que el lookup es seguro mientras pasemos el org_id.
                
                # Si queremos persistir en memoria, deberíamos usar {org_id}:{flow_type}
                # pero el registry actual no soporta eso bien en list_flows.
                
                return BoundDynamicFlow
                
        except Exception as exc:
            logger.error("Error loading flow '%s' from DB: %s", flow_type, exc)
            return None

    def create(self, name: str, org_id: str | None = None, **kwargs: Any) -> Any:
        """Instantiate a registered Flow by name."""
        return self.get(name, org_id=org_id)(org_id=org_id, **kwargs)

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
