"""Performance benchmarks P6.1-P6.4 — Paso 6: Performance & Observabilidad.

P6.1: resolve_tools 50 tools mock registry -> <100ms
P6.2: WorkflowDefinition 10 steps + 5 agents -> <50ms
P6.3: sanitize_output 1MB string with secrets -> <500ms
P6.4: MCPPool._is_circuit_open overhead -> <1ms
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock
from uuid import uuid4

from src.crews.factory import AgentFactory
from src.flows.workflow_definition import WorkflowDefinition
from src.mcp.sanitizer import sanitize_output
from src.tools.mcp_pool import MCPPool
from src.tools.registry import tool_registry

from .conftest import make_agent_definition, make_secret_string, make_step_definition

# ── Helpers ───────────────────────────────────────────────────────


class _MockPerfTool:
    def __init__(self, org_id: str | None = None) -> None:
        self.org_id = org_id


def _register_mock_tools(count: int) -> list[str]:
    """Register *count* mock tool classes in tool_registry. Return names."""
    names: list[str] = []
    for i in range(count):
        name = f"_perf_mock_tool_{i}"
        names.append(name)
        cls = type(f"PerfMockTool{i}", (_MockPerfTool,), {})
        tool_registry._tools[name] = cls
    return names


def _unregister_mock_tools(names: list[str]) -> None:
    for name in names:
        tool_registry._tools.pop(name, None)


def _warmup(fn, *args, **kwargs):
    """Run 1 warmup iteration, discard result."""
    fn(*args, **kwargs)


def _report_time(name: str, elapsed: float) -> None:
    """Print machine-readable timing marker for CLI to parse."""
    print(f"BENCH_TIME: {name} {elapsed:.6f}s")


# ── P6.1: resolve_tools 50 tools <100ms ───────────────────────────


class TestP6_1ResolveTools50:
    """P6.1: AgentFactory.resolve_tools with 50 mock tools."""

    def test_resolve_tools_50_under_100ms(self):
        count = 50
        names = _register_mock_tools(count)
        org_id = str(uuid4())
        try:
            _warmup(AgentFactory.resolve_tools, names, org_id, async_mode=False)
            start = time.perf_counter()
            tools = AgentFactory.resolve_tools(names, org_id, async_mode=False)
            elapsed = time.perf_counter() - start
            _report_time("resolve_tools_50", elapsed)
            assert elapsed < 0.10, (
                f"resolve_tools 50 tools took {elapsed*1000:.1f}ms, expected <100ms"
            )
            assert len(tools) == count
        finally:
            _unregister_mock_tools(names)

    def test_resolve_tools_50_returns_all_tools(self):
        count = 50
        names = _register_mock_tools(count)
        org_id = str(uuid4())
        try:
            tools = AgentFactory.resolve_tools(names, org_id, async_mode=False)
            assert len(tools) == count
        finally:
            _unregister_mock_tools(names)


# ── P6.2: WorkflowDefinition 10 steps + 5 agents <50ms ────────────


class TestP6_2WorkflowDefinitionValidation:
    """P6.2: WorkflowDefinition validation with 10 steps + 5 agents."""

    def _build_workflow_dict(self) -> dict:
        roles = [f"bench_agent_{i}" for i in range(5)]
        agents = [make_agent_definition(r) for r in roles]
        steps = []
        for i in range(10):
            role = roles[i % 5]
            dep = None if i == 0 else [steps[i - 1]["id"]]
            steps.append(make_step_definition(role, step_id=f"step_{i}"))
            steps[-1]["depends_on"] = dep
        return {
            "name": "Benchmark Workflow",
            "description": "10-step 5-agent workflow for performance benchmark",
            "flow_type": "bench_perf_test",
            "steps": steps,
            "agents": agents,
            "category": "test",
        }

    def test_workflow_definition_10x5_under_50ms(self):
        data = self._build_workflow_dict()
        _warmup(WorkflowDefinition, **data)
        start = time.perf_counter()
        wd = WorkflowDefinition(**data)
        elapsed = time.perf_counter() - start
        _report_time("workflow_definition_10x5", elapsed)
        assert elapsed < 0.050, (
            f"WorkflowDefinition validation took {elapsed*1000:.1f}ms, expected <50ms"
        )
        assert isinstance(wd, WorkflowDefinition)
        assert len(wd.steps) == 10
        assert len(wd.agents) == 5

    def test_workflow_definition_10x5_validates_correctly(self):
        data = self._build_workflow_dict()
        wd = WorkflowDefinition(**data)
        assert wd.name == "Benchmark Workflow"
        assert wd.flow_type == "bench_perf_test"
        assert len(wd.steps) == 10
        assert len(wd.agents) == 5


# ── P6.3: sanitize_output 1MB <500ms ──────────────────────────────


class TestP6_3Sanitize1MB:
    """P6.3: sanitize_output with 1MB string containing secrets."""

    def test_sanitize_1mb_under_500ms(self):
        size = 1024 * 1024
        large_str = make_secret_string(size, secret_count=100)

        _warmup(sanitize_output, large_str)
        start = time.perf_counter()
        result = sanitize_output(large_str)
        elapsed = time.perf_counter() - start

        _report_time("sanitize_1mb", elapsed)
        assert elapsed < 0.50, (
            f"santize_output 1MB took {elapsed*1000:.1f}ms, expected <500ms"
        )
        assert isinstance(result, str)
        assert "[REDACTED]" in result

    def test_sanitize_1mb_redacts_secrets(self):
        size = 1024 * 1024
        large_str = make_secret_string(size, secret_count=100)

        result = sanitize_output(large_str)
        assert "[REDACTED]" in result
        assert "sk_live_" not in result
        assert "ghp_" not in result


# ── P6.4: MCPPool._is_circuit_open overhead <1ms ─────────────────


class TestP6_4CircuitBreakerOverhead:
    """P6.4: MCPPool._is_circuit_open overhead in both states."""

    def setup_pool_state(self, is_open: bool) -> tuple[MCPPool, str]:
        pool = MCPPool.get()
        key = f"bench_test:{uuid4()}"
        if is_open:
            pool._health[key] = {"failures": 5.0, "last_check": time.time()}
        else:
            pool._health[key] = {"failures": 0.0, "last_check": time.time()}
        pool._adapters[key] = MagicMock()
        return pool, key

    def test_is_circuit_open_closed_under_1ms(self):
        pool, key = self.setup_pool_state(is_open=False)

        _warmup(pool._is_circuit_open, key)
        start_ns = time.perf_counter_ns()
        result = pool._is_circuit_open(key)
        elapsed_ns = time.perf_counter_ns() - start_ns

        _report_time("circuit_closed", elapsed_ns / 1_000_000_000)
        assert result is False
        assert elapsed_ns < 1_000_000, (
            f"_is_circuit_open (closed) took {elapsed_ns/1000:.1f}us, expected <1ms"
        )

    def test_is_circuit_open_open_under_1ms(self):
        pool, key = self.setup_pool_state(is_open=True)

        _warmup(pool._is_circuit_open, key)
        start_ns = time.perf_counter_ns()
        result = pool._is_circuit_open(key)
        elapsed_ns = time.perf_counter_ns() - start_ns

        _report_time("circuit_open", elapsed_ns / 1_000_000_000)
        assert result is True
        assert elapsed_ns < 1_000_000, (
            f"_is_circuit_open (open) took {elapsed_ns/1000:.1f}us, expected <1ms"
        )

    def test_is_circuit_open_both_states_independent(self):
        pool, key_closed = self.setup_pool_state(is_open=False)
        _, key_open = self.setup_pool_state(is_open=True)

        elapsed_closed = 0
        elapsed_open = 0

        for _ in range(5):
            t0 = time.perf_counter_ns()
            r1 = pool._is_circuit_open(key_closed)
            t1 = time.perf_counter_ns()
            r2 = pool._is_circuit_open(key_open)
            t2 = time.perf_counter_ns()
            elapsed_closed += t1 - t0
            elapsed_open += t2 - t1
            assert r1 is False
            assert r2 is True

        avg_closed_us = (elapsed_closed / 5) / 1000
        avg_open_us = (elapsed_open / 5) / 1000
        assert avg_closed_us < 1000, f"avg closed {avg_closed_us:.1f}us"
        assert avg_open_us < 1000, f"avg open {avg_open_us:.1f}us"
