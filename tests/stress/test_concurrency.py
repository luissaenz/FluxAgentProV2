"""Stress tests S4.1-S4.3: Concurrencia y alta carga.

S4.1: resolve_tools con 500 tools registradas
S4.2: 50 DynamicWorkflow concurrentes en asyncio.gather
S4.3: MCPPool.reset 100 veces consecutivas
"""

from __future__ import annotations

import asyncio
import gc
import os
import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.crews.factory import AgentFactory
from src.flows.dynamic_flow import DynamicWorkflow
from src.flows.registry import flow_registry
from src.tools.mcp_pool import MCPPool
from src.tools.registry import tool_registry

# ── Helpers ──────────────────────────────────────────────────────

def _get_tool_count() -> int:
    return int(os.environ.get("STRESS_TOOLS_COUNT", "500"))


def _get_workflow_count() -> int:
    return int(os.environ.get("STRESS_WORKFLOWS_COUNT", "50"))


class _MockStressTool:
    """Minimal tool class that accepts org_id, supports weakref."""
    def __init__(self, org_id: str | None = None) -> None:
        self.org_id = org_id


def _register_mock_tools(count: int) -> list[str]:
    """Register *count* mock tool classes in tool_registry. Return names."""
    names: list[str] = []
    for i in range(count):
        name = f"_stress_mock_tool_{i}"
        names.append(name)
        cls = type(
            f"StressMockTool{i}",
            (_MockStressTool,),
            {},
        )
        tool_registry._tools[name] = cls
    return names


def _unregister_mock_tools(names: list[str]) -> None:
    for name in names:
        tool_registry._tools.pop(name, None)


def _make_step_definition(agent_role: str) -> dict:
    return {
        "id": "step_1",
        "name": "Process",
        "description": "Process the request in stress test",
        "agent_role": agent_role,
        "depends_on": None,
        "requires_approval": False,
    }


def _make_agent_definition(role: str) -> dict:
    return {
        "role": role,
        "goal": "Complete the assigned task in stress test",
        "backstory": "Stress test agent for concurrent execution",
        "allowed_tools": [],
        "rules": [],
        "model": "claude-sonnet-4-20250514",
        "max_iter": 3,
    }


# ── Fixtures ─────────────────────────────────────────────────────


# ── S4.1: resolve_tools 500 tools ───────────────────────────────


class TestS4_1ResolveTools500:
    """S4.1: resolve_tools performance and memory."""

    @pytest.mark.asyncio
    async def test_resolve_tools_500_completes_under_2s(self):
        """resolve_tools con 500 tools registradas completa en <2s."""
        count = _get_tool_count()
        names = _register_mock_tools(count)
        org_id = str(uuid4())
        try:
            start = time.time()
            tools = AgentFactory.resolve_tools(names, org_id, async_mode=False)
            elapsed = time.time() - start
            assert elapsed < 2.0, (
                f"resolve_tools took {elapsed:.2f}s, expected <2s"
            )
            assert len(tools) == count
        finally:
            _unregister_mock_tools(names)

    @pytest.mark.asyncio
    async     def test_resolve_tools_500_no_memory_leak(self):
        """resolve_tools no retiene referencias post-scope."""
        count = _get_tool_count()
        names = _register_mock_tools(count)
        org_id = str(uuid4())

        try:
            # Count _MockStressTool instances before resolve
            gc.collect()
            gc.collect()
            before = len(
                [o for o in gc.get_objects() if isinstance(o, _MockStressTool)]
            )

            # Resolve — instances created
            tools = AgentFactory.resolve_tools(names, org_id, async_mode=False)
            assert len(tools) == count

            # Release all references
            del tools
            gc.collect()
            gc.collect()

            after = len(
                [o for o in gc.get_objects() if isinstance(o, _MockStressTool)]
            )
            assert after == before, (
                f"{after - before} _MockStressTool instances leaked post-scope"
            )
        finally:
            _unregister_mock_tools(names)


# ── S4.2: 50 DynamicWorkflow concurrentes ────────────────────────


class TestS4_2ConcurrentWorkflows:
    """S4.2: 50 DynamicWorkflow en asyncio.gather completan sin excepción."""

    @pytest.mark.asyncio
    async def test_50_workflows_concurrent_no_exceptions(self):
        """50 DynamicWorkflow en asyncio.gather completan sin excepción."""
        n_workflows = _get_workflow_count()
        mock_crew = MagicMock()

        async def _mock_run_async(**kwargs):  # noqa: ARG001
            await asyncio.sleep(0.01)
            return MagicMock(raw=f"stress_result_{id(kwargs)}")

        mock_crew.run_async = AsyncMock(side_effect=_mock_run_async)
        mock_crew.get_last_tokens_used = MagicMock(return_value=0)

        workflows = []
        org_id = str(uuid4())

        for i in range(n_workflows):
            flow_type = f"_stress_flow_{i}"
            role = f"_stress_agent_{i}"
            definition = {
                "name": f"Stress Workflow {i}",
                "description": "Stress test workflow for concurrent execution",
                "flow_type": flow_type,
                "steps": [_make_step_definition(role)],
                "agents": [_make_agent_definition(role)],
            }
            DynamicWorkflow.register(flow_type, definition)
            flow_class = flow_registry._flows[flow_type.lower()]
            flow = flow_class(org_id=org_id)
            flow.state = MagicMock()
            flow.state.input_data = {"index": i}
            flow.persist_state = AsyncMock()
            flow.emit_event = AsyncMock()
            flow.get_last_tokens_used = MagicMock(return_value=0)
            flow._template_definition = definition
            flow._flow_type = flow_type
            workflows.append(flow)

        with patch("src.flows.dynamic_flow.BaseCrew", return_value=mock_crew):
            results = await asyncio.gather(
                *[flow._run_crew() for flow in workflows],
                return_exceptions=True,
            )

        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, (
            f"{len(exceptions)} workflow(s) raised exceptions: {exceptions}"
        )
        assert all(isinstance(r, dict) for r in results), (
            "All results must be Dict[str, Any]"
        )
        assert all(len(r) >= 1 for r in results), (
            "Each result must contain at least one step"
        )


# ── S4.3: MCPPool.reset 100 veces ────────────────────────────────


class TestS4_3MCPPoolReset100:
    """S4.3: MCPPool.reset 100 veces consecutivas."""

    def test_reset_100_times_no_error(self):
        """MCPPool.reset() 100 veces sin error."""
        for _ in range(100):
            MCPPool.reset()
        # Should not raise

    def test_after_100_resets_pool_is_clean(self):
        """Tras 100 resets, MCPPool.get() retorna instancia limpia."""
        for _ in range(100):
            MCPPool.reset()

        pool = MCPPool.get()
        assert pool._health == {} or all(
            len(v) == 0 for v in pool._health.values()
        ), "_health debe estar vacío tras reset"
        assert pool._adapters == {}, "_adapters debe estar vacío tras reset"
