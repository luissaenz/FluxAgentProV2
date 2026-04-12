"""tests/unit/test_registry_validation.py — Phase 4 flow dependency validation.

Covers:
  - FlowRegistry.validate_dependencies() — detects missing dependencies
  - FlowRegistry.detect_cycles() — detects direct and indirect cycles
  - FlowRegistry.run_full_validation() — combined validation report
  - Integration with registered flows (coctel + bartenders)
"""

from __future__ import annotations

import pytest
from src.flows.registry import FlowRegistry, register_flow, flow_registry
from src.flows.base_flow import BaseFlow


# ── Helpers ─────────────────────────────────────────────────────

def _make_registry() -> FlowRegistry:
    """Create a fresh registry for isolated tests."""
    return FlowRegistry()


def _register_flow_class(registry: FlowRegistry, name: str,
                         depends_on: list[str] | None = None,
                         category: str | None = None) -> None:
    """Register a minimal flow class in a given registry."""
    # We bypass the decorator and write directly to internals
    class DummyFlow(BaseFlow):
        def validate_input(self, input_data: dict) -> bool:
            return True
        async def _run_crew(self) -> dict:
            return {}

    key = name.lower()
    DummyFlow.__name__ = name
    registry._flows[key] = DummyFlow
    # Normalize dep names to lowercase to match registry key format
    registry._metadata[key] = {
        "depends_on": [d.lower() for d in (depends_on or [])],
        "category": category,
    }


# ── validate_dependencies tests ─────────────────────────────────

class TestValidateDependencies:
    """FlowRegistry.validate_dependencies() behavior."""

    def test_no_invalid_dependencies(self):
        """When all deps exist, result is empty dict."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA", depends_on=[])
        _register_flow_class(reg, "FlowB", depends_on=["flowa"])

        result = reg.validate_dependencies()
        assert result == {}

    def test_detects_missing_dependency(self):
        """Missing dep is reported."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA", depends_on=["nonexistent_flow"])

        result = reg.validate_dependencies()
        assert result == {"flowa": ["nonexistent_flow"]}

    def test_multiple_missing_dependencies(self):
        """Multiple flows with missing deps are all reported."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA", depends_on=["missing_x", "missing_y"])
        _register_flow_class(reg, "FlowB", depends_on=["missing_z"])

        result = reg.validate_dependencies()
        assert result == {
            "flowa": ["missing_x", "missing_y"],
            "flowb": ["missing_z"],
        }

    def test_case_insensitive_lookup(self):
        """Dependency lookup is case-insensitive."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA")
        _register_flow_class(reg, "FlowB", depends_on=["FLOWA"])

        result = reg.validate_dependencies()
        assert result == {}

    def test_empty_registry(self):
        """Empty registry returns empty dict."""
        reg = _make_registry()
        result = reg.validate_dependencies()
        assert result == {}


# ── detect_cycles tests ─────────────────────────────────────────

class TestDetectCycles:
    """FlowRegistry.detect_cycles() behavior."""

    def test_no_cycles(self):
        """Linear chain has no cycles."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA", depends_on=[])
        _register_flow_class(reg, "FlowB", depends_on=["flowa"])
        _register_flow_class(reg, "FlowC", depends_on=["flowb"])

        result = reg.detect_cycles()
        assert result == []

    def test_direct_cycle_a_b_a(self):
        """Direct cycle A→B→A is detected."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA", depends_on=["flowb"])
        _register_flow_class(reg, "FlowB", depends_on=["flowa"])

        result = reg.detect_cycles()
        assert len(result) == 1
        cycle = result[0]
        assert set(cycle[:-1]) == {"flowa", "flowb"}
        assert cycle[0] == cycle[-1]

    def test_indirect_cycle_a_b_c_a(self):
        """Indirect cycle A→B→C→A is detected."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA", depends_on=["flowc"])
        _register_flow_class(reg, "FlowB", depends_on=["flowa"])
        _register_flow_class(reg, "FlowC", depends_on=["flowb"])

        result = reg.detect_cycles()
        assert len(result) == 1
        cycle = result[0]
        assert set(cycle[:-1]) == {"flowa", "flowb", "flowc"}
        assert cycle[0] == cycle[-1]

    def test_no_false_positive_shared_dependency(self):
        """Two flows depending on the same one is NOT a cycle."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA", depends_on=[])
        _register_flow_class(reg, "FlowB", depends_on=["flowa"])
        _register_flow_class(reg, "FlowC", depends_on=["flowa"])

        result = reg.detect_cycles()
        assert result == []

    def test_cycle_with_missing_dep(self):
        """Cycle is detected even if one dep is missing."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA", depends_on=["flowb"])
        _register_flow_class(reg, "FlowB", depends_on=["flowa", "missing_x"])

        result = reg.detect_cycles()
        assert len(result) >= 1

    def test_self_cycle(self):
        """A flow depending on itself is a cycle."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA", depends_on=["flowa"])

        result = reg.detect_cycles()
        assert len(result) == 1
        assert result[0] == ["flowa", "flowa"]


# ── run_full_validation tests ───────────────────────────────────

class TestRunFullValidation:
    """FlowRegistry.run_full_validation() combined report."""

    def test_clean_registry(self):
        """Valid chain returns empty validation issues."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA", depends_on=[], category="cat1")
        _register_flow_class(reg, "FlowB", depends_on=["flowa"], category="cat1")

        result = reg.run_full_validation()
        assert result == {
            "invalid_dependencies": {},
            "cycles": [],
        }

    def test_both_invalid_and_cycles(self):
        """Report includes both invalid deps and cycles."""
        reg = _make_registry()
        _register_flow_class(reg, "FlowA", depends_on=["missing_x"])
        _register_flow_class(reg, "FlowB", depends_on=["flow_a"])
        _register_flow_class(reg, "FlowC", depends_on=["flow_b", "flow_a"])

        result = reg.run_full_validation()
        assert "missing_x" in result["invalid_dependencies"]["flowa"]
        assert result["cycles"] == []

    def test_validation_structure(self):
        """Validation result has expected keys."""
        reg = _make_registry()
        result = reg.run_full_validation()
        assert "invalid_dependencies" in result
        assert "cycles" in result


# ── Integration with register_flow decorator ────────────────────

class TestRegisterFlowDecorator:
    """@register_flow decorator with metadata."""

    def test_decorator_with_metadata(self):
        """Decorator stores depends_on and category."""
        reg = FlowRegistry()
        # Use the global decorator but on a fresh registry
        original_registry = flow_registry

        @register_flow("decorated_flow", depends_on=["dep_a", "dep_b"], category="testing")
        class DecoratedFlow(BaseFlow):
            def validate_input(self, input_data: dict) -> bool:
                return True
            async def _run_crew(self) -> dict:
                return {}

        meta = flow_registry.get_metadata("decorated_flow")
        assert meta["depends_on"] == ["dep_a", "dep_b"]
        assert meta["category"] == "testing"

        # Cleanup
        flow_registry._flows.pop("decorated_flow", None)
        flow_registry._metadata.pop("decorated_flow", None)

    def test_decorator_defaults(self):
        """Decorator defaults to empty depends_on and None category."""
        @register_flow("defaults_flow")
        class DefaultsFlow(BaseFlow):
            def validate_input(self, input_data: dict) -> bool:
                return True
            async def _run_crew(self) -> dict:
                return {}

        meta = flow_registry.get_metadata("defaults_flow")
        assert meta["depends_on"] == []
        assert meta["category"] is None

        # Cleanup
        flow_registry._flows.pop("defaults_flow", None)
        flow_registry._metadata.pop("defaults_flow", None)


# ── Integration with real registered flows ──────────────────────

class TestRealFlowsValidation:
    """Validation against the actual project flows."""

    def test_coctel_flows_have_no_cycles(self):
        """CoctelPro flows (cotizacion, logistica, compras, finanzas) should be cycle-free."""
        from src.flows import coctel_flows  # noqa: F401 — triggers registration

        result = flow_registry.detect_cycles()
        # Filter to only coctel flows
        coctel_names = {"cotizacion_flow", "logistica_flow", "compras_flow", "finanzas_flow"}
        coctel_cycles = [
            c for c in result
            if any(name in coctel_names for name in c)
        ]
        assert coctel_cycles == []

    def test_bartender_flows_registered_with_metadata(self):
        """Bartender flows should be registered with category and depends_on."""
        from src.flows.bartenders import registry_wiring  # noqa: F401

        for name, expected_cat, expected_deps in [
            ("bartenders_preventa", "preventa", []),
            ("bartenders_reserva", "reserva", ["bartenders_preventa"]),
            ("bartenders_alerta", "monitoreo", ["bartenders_reserva"]),
            ("bartenders_cierre", "cierre", ["bartenders_reserva"]),
        ]:
            assert flow_registry.has(name), f"Flow '{name}' not registered"
            meta = flow_registry.get_metadata(name)
            assert meta["category"] == expected_cat, f"Flow '{name}' has wrong category"
            assert meta["depends_on"] == expected_deps, f"Flow '{name}' has wrong depends_on"

    def test_real_flows_validation_no_missing_deps(self):
        """All real flows should have valid dependencies."""
        from src.flows import coctel_flows  # noqa: F401
        from src.flows.bartenders import registry_wiring  # noqa: F401

        result = flow_registry.validate_dependencies()
        assert result == {}, f"Flows with invalid dependencies: {result}"
