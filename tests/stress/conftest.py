"""Local conftest for stress tests — isolates from global conftest.

Provides shared fixtures: MCPPool reset, flow_registry save/restore,
and reusable helpers for benchmark tests.
"""

from __future__ import annotations

import pytest

from src.flows.registry import flow_registry
from src.tools.mcp_pool import MCPPool

# ── Fixtures ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_pool():
    """Reset singleton MCPPool before and after each stress test."""
    MCPPool.reset()
    yield
    MCPPool.reset()


@pytest.fixture(autouse=True)
def _clean_flow_registry():
    """Save and restore flow_registry to isolate stress tests."""
    saved_flows = dict(flow_registry._flows)
    saved_metadata = dict(flow_registry._metadata)
    yield
    flow_registry._flows.clear()
    flow_registry._flows.update(saved_flows)
    flow_registry._metadata.clear()
    flow_registry._metadata.update(saved_metadata)


# ── Reusable helpers ──────────────────────────────────────────────


def make_step_definition(agent_role: str, step_id: str = "step_1") -> dict:
    return {
        "id": step_id,
        "name": "Process",
        "description": f"Process the request (role={agent_role})",
        "agent_role": agent_role,
        "depends_on": None,
        "requires_approval": False,
    }


def make_agent_definition(role: str) -> dict:
    return {
        "role": role,
        "goal": "Complete the assigned task in benchmark test",
        "backstory": "Benchmark test agent for performance validation",
        "allowed_tools": [],
        "rules": [],
        "model": "claude-sonnet-4-20250514",
        "max_iter": 3,
    }


def make_secret_string(target_bytes: int, secret_count: int = 100) -> str:
    """Generate a string of approx *target_bytes* with ~*secret_count* secrets."""
    secret_templates = [
        "sk_live_" + "a" * 24,
        "Bearer " + "x" * 40 + "=",
        "ghp_" + "b" * 36,
        "AIza" + "c" * 35,
        "xoxb-" + "d" * 24,
    ]
    safe_line = "INFO: Processing request completed successfully in 1.23s. " * 5
    block = safe_line
    for _ in range(secret_count // len(secret_templates) + 1):
        for s in secret_templates:
            block += f"Token: {s}. " + safe_line[:50]
    repeats = max(1, target_bytes // len(block))
    return (block * repeats)[:target_bytes]
