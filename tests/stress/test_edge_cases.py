"""Edge-case tests S4.4-S4.7: Condiciones de borde.

S4.4: flow_type duplicado en DynamicWorkflow.register
S4.5: sanitize_output con string 10MB
S4.6: resolve_tools con org_id=""
S4.7: WorkflowDefinition con input_data 20 niveles anidados
"""

from __future__ import annotations

import os
import time

import pytest

from src.crews.factory import AgentFactory
from src.flows.dynamic_flow import DynamicWorkflow
from src.flows.registry import flow_registry
from src.flows.workflow_definition import WorkflowDefinition
from src.mcp.sanitizer import sanitize_output
from src.tools.registry import tool_registry

# ── Helpers ──────────────────────────────────────────────────────

def _get_sanitizer_size() -> int:
    return int(os.environ.get("STRESS_SANITIZER_SIZE", str(10 * 1024 * 1024)))


def _get_json_depth() -> int:
    return int(os.environ.get("STRESS_JSON_DEPTH", "20"))


def _make_nested_dict(depth: int) -> dict:
    """Build a nested dict of *depth* levels. inner value is a leaf string."""
    if depth <= 0:
        return {"value": "deep_leaf", "arr": [1, 2, 3]}
    return {"lvl": _make_nested_dict(depth - 1)}


def _make_10mb_string(target_bytes: int) -> str:
    """Generate a string of approximately *target_bytes* bytes."""
    # Fill with safe text + occasional secret patterns
    base_text = "Hello, this is a safe log line without credentials. " * 10
    secret_line = "Token: REDACTED_PLACEHOLDER_KEY. "  # Fake test token — no real secret
    secret_part = secret_line + "Safe data here. " * 5  # ~200 chars per block
    # Target: mix of safe + secret
    block = (base_text + secret_part) * 3  # ~4500 chars
    repeats = max(1, target_bytes // len(block))
    result = (block * repeats)[:target_bytes]
    return result


def _make_step_definition(agent_role: str) -> dict:
    return {
        "id": "step_1",
        "name": "Process",
        "description": "Process the request in edge-case test",
        "agent_role": agent_role,
        "depends_on": None,
        "requires_approval": False,
    }


def _make_agent_definition(role: str) -> dict:
    return {
        "role": role,
        "goal": "Complete the assigned task in edge-case test",
        "backstory": "Edge-case test agent",
        "allowed_tools": [],
        "rules": [],
        "model": "claude-sonnet-4-20250514",
        "max_iter": 3,
    }


# ── Fixtures ─────────────────────────────────────────────────────


# ── S4.4: flow_type duplicado ────────────────────────────────────


class TestS4_4DuplicateFlowType:
    """S4.4: DynamicWorkflow.register sobrescribe sin error."""

    def test_register_same_flow_type_override(self):
        """register("test_flow", def1).register("test_flow", def2) sobrescribe."""
        def1 = {
            "name": "Original",
            "description": "Original workflow definition",
            "flow_type": "test_flow",
            "category": "test",
            "steps": [_make_step_definition("agent_a")],
            "agents": [_make_agent_definition("agent_a")],
        }
        def2 = {
            "name": "Override",
            "description": "Override workflow definition",
            "flow_type": "test_flow",
            "category": "test",
            "steps": [_make_step_definition("agent_b")],
            "agents": [_make_agent_definition("agent_b")],
        }

        DynamicWorkflow.register("test_flow", def1)
        DynamicWorkflow.register("test_flow", def2)

        assert "test_flow" in flow_registry._flows
        cls = flow_registry._flows["test_flow"]
        assert cls._template_definition["name"] == "Override"
        assert cls._template_definition != def1

    def test_register_same_flow_no_exception(self):
        """Registrar mismo flow_type dos veces no lanza excepción."""
        defn = {
            "name": "Dup",
            "description": "Duplicate flow registration test",
            "flow_type": "dup_flow",
            "steps": [_make_step_definition("agent_x")],
            "agents": [_make_agent_definition("agent_x")],
        }
        DynamicWorkflow.register("dup_flow", defn)
        DynamicWorkflow.register("dup_flow", defn)
        # Should not raise


# ── S4.5: sanitize 10MB ──────────────────────────────────────────


class TestS4_5SanitizeLargeString:
    """S4.5: sanitize_output con string 10MB."""

    def test_sanitize_10mb_under_5s(self):
        """sanitize_output(string 10MB) completa en <5s."""
        size = _get_sanitizer_size()
        large_str = _make_10mb_string(size)

        start = time.time()
        result = sanitize_output(large_str)
        elapsed = time.time() - start

        assert elapsed < 5.0, (
            f"sanitize_output({size} bytes) took {elapsed:.2f}s, expected <5s"
        )
        assert isinstance(result, str)
        assert "[REDACTED]" in result, (
            "Secrets in the large string should be redacted"
        )

    def test_sanitize_10mb_no_memory_error(self):
        """sanitize_output(string 10MB) no lanza MemoryError."""
        size = _get_sanitizer_size()
        large_str = _make_10mb_string(size)

        try:
            result = sanitize_output(large_str)
            assert isinstance(result, str)
        except MemoryError:
            pytest.fail("sanitize_output raised MemoryError on 10MB input")

    def test_sanitize_10mb_preserves_structure(self):
        """sanitize_output(string 10MB) preserva longitud aprox."""
        size = _get_sanitizer_size()
        large_str = _make_10mb_string(size)

        result = sanitize_output(large_str)
        # Sanitized result should be no longer than original
        assert len(result) <= len(large_str) + 1
        # Should still be large (still has non-secret content)
        assert len(result) > size * 0.9


# ── S4.6: org_id="" ──────────────────────────────────────────────


class TestS4_6EmptyOrgId:
    """S4.6: resolve_tools with empty org_id behaves gracefully."""

    def test_resolve_tools_empty_org_id_no_exception(self):
        """resolve_tools with empty org_id does not raise."""
        name = "_stress_empty_org_tool"
        cls = type("EmptyOrgTool", (), {"__init__": lambda self, org_id=None: None})
        tool_registry._tools[name] = cls
        try:
            tools = AgentFactory.resolve_tools([name], org_id="", async_mode=False)
            assert isinstance(tools, list)
        finally:
            tool_registry._tools.pop(name, None)

    def test_resolve_tools_empty_org_id_returns_list(self):
        """resolve_tools with empty org_id returns a list."""
        tools = AgentFactory.resolve_tools(
            ["_nonexistent_tool_xyz"], org_id="", async_mode=False,
        )
        assert isinstance(tools, list)


# ── S4.7: JSON 20 niveles ────────────────────────────────────────


class TestS4_7DeeplyNestedJSON:
    """S4.7: WorkflowDefinition with deeply nested input_data (20 levels)."""

    def test_workflow_definition_deep_nested_no_recursion_error(self):
        """WorkflowDefinition with 20-level nested input_data no RecursionError."""
        depth = _get_json_depth()
        nested = _make_nested_dict(depth)

        try:
            wd = WorkflowDefinition(
                name="Deep Nest Test",
                description="Testing deeply nested input data " * 3,
                flow_type="deep_nest_test",
                steps=[_make_step_definition("agent_deep")],
                agents=[_make_agent_definition("agent_deep")],
                input_data=nested,
            )
            assert wd.name == "Deep Nest Test"
            assert wd.flow_type == "deep_nest_test"
        except RecursionError:
            pytest.fail("WorkflowDefinition raised RecursionError on 20-level nested dict")

    def test_workflow_definition_deep_validation_no_timeout(self):
        """WorkflowDefinition validation pasa sin timeout."""
        depth = _get_json_depth()
        nested = _make_nested_dict(depth)

        start = time.time()
        wd = WorkflowDefinition(
            name="Deep Timeout Test",
            description="Testing deeply nested input data timeout " * 3,
            flow_type="deep_timeout_test",
            steps=[_make_step_definition("agent_t")],
            agents=[_make_agent_definition("agent_t")],
            input_data=nested,
        )
        elapsed = time.time() - start

        assert elapsed < 2.0, (
            f"WorkflowDefinition validation took {elapsed:.2f}s, expected <2s"
        )
        assert isinstance(wd, WorkflowDefinition)
